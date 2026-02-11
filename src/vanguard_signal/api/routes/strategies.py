"""
strategies.py — API routes for strategy management.

Provides endpoints for listing, deploying, and managing trading strategies.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
import uuid

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field
import logging

from vanguard_signal.strategies.registry import get_registry
from vanguard_signal.api.deps import get_user_id, get_db
from vanguard_signal.schema.models.user import User
from vanguard_signal.schema.database import get_session
from vanguard_signal.schema.models.deployed_strategy import DeployedStrategy as DeployedStrategyModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/strategies", tags=["strategies"])


class StrategyInfo(BaseModel):
    """Strategy information response model."""
    id: str = Field(..., description="Strategy ID")
    name: str = Field(..., description="Strategy name")
    description: str = Field(..., description="Strategy description")
    type: str = Field(..., description="Strategy type")
    version: str = Field(..., description="Strategy version")
    author: str = Field(..., description="Strategy author")
    parameters: Dict[str, Any] = Field(..., description="Strategy parameters")


class DeployStrategyRequest(BaseModel):
    """Request model for deploying a strategy."""
    strategy_id: str = Field(..., description="ID of the strategy to deploy")
    name: str = Field(..., description="Name for the deployment")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Strategy parameters")
    capital: float = Field(..., description="Initial capital allocation")


class DeployedStrategy(BaseModel):
    """Deployed strategy response model."""
    id: str = Field(..., description="Deployment ID")
    strategy_id: str = Field(..., description="Strategy ID")
    name: str = Field(..., description="Deployment name")
    status: str = Field(..., description="Deployment status")
    capital: float = Field(..., description="Allocated capital")
    performance: Dict[str, Any] = Field(default_factory=dict, description="Performance metrics")
    created_at: str = Field(..., description="Creation timestamp")


@router.get("/", response_model=List[StrategyInfo])
async def list_strategies(
    strategy_type: Optional[str] = None,
    current_user_id: str = Depends(get_user_id),
) -> List[StrategyInfo]:
    """
    List available trading strategies.

    Args:
        strategy_type: Optional filter by strategy type
        current_user: Current authenticated user (optional)

    Returns:
        List of available strategies
    """
    try:
        registry = get_registry()

        # Get all strategy IDs
        all_strategies = registry.list_strategies()

        # Filter by type if specified
        if strategy_type:
            from vanguard_signal.strategies.base import StrategyType
            try:
                st_type = StrategyType(strategy_type)
                all_strategies = registry.list_strategies_by_type(st_type)
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid strategy type: {strategy_type}"
                )

        # Get detailed info for each strategy
        strategies = []
        for strategy_id in all_strategies:
            info = registry.get_strategy_info(strategy_id)
            if info:
                strategies.append(StrategyInfo(**info))

        return strategies

    except Exception as e:
        logger.error(f"Failed to list strategies: {e}")
        raise HTTPException(status_code=500, detail="Failed to list strategies")


@router.get("/{strategy_id}", response_model=StrategyInfo)
async def get_strategy(
    strategy_id: str,
    current_user_id: str = Depends(get_user_id),
) -> StrategyInfo:
    """
    Get detailed information about a specific strategy.

    Args:
        strategy_id: ID of the strategy
        current_user: Current authenticated user (optional)

    Returns:
        Strategy information
    """
    try:
        registry = get_registry()
        info = registry.get_strategy_info(strategy_id)

        if not info:
            raise HTTPException(status_code=404, detail=f"Strategy {strategy_id} not found")

        return StrategyInfo(**info)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get strategy {strategy_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to get strategy")


@router.post("/deploy", response_model=DeployedStrategy)
async def deploy_strategy(
    request: DeployStrategyRequest,
    background_tasks: BackgroundTasks,
    current_user_id: str = Depends(get_user_id),
    session: AsyncSession = Depends(get_db),
) -> DeployedStrategy:
    """
    Deploy a trading strategy.

    Args:
        request: Deployment request
        background_tasks: FastAPI background tasks
        current_user: Current authenticated user (optional)

    Returns:
        Deployed strategy information
    """
    try:
        registry = get_registry()

        # Validate strategy exists
        if request.strategy_id not in registry._strategies:
            raise HTTPException(
                status_code=404,
                detail=f"Strategy {request.strategy_id} not found"
            )

        # Create strategy instance for validation
        strategy = registry.create_strategy(request.strategy_id)
        if not strategy:
            raise HTTPException(
                status_code=400,
                detail=f"Failed to create strategy {request.strategy_id}"
            )

        # Validate parameters
        if request.parameters:
            strategy.set_parameters(request.parameters)
            errors = strategy.validate_config()
            if errors:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid parameters: {errors}"
                )

        # Create DB model instance
        # Resolve creating user email when available
        created_by_email = None
        if current_user_id and current_user_id != "anonymous":
            try:
                db_user = await session.get(User, current_user_id)
                created_by_email = getattr(db_user, 'email', None) if db_user else None
            except Exception:
                created_by_email = None

        model = DeployedStrategyModel(
            strategy_id=request.strategy_id,
            name=request.name,
            status="deployed",
            capital=request.capital,
            performance={},
            created_by=created_by_email,
        )

        # Persist and flush to populate defaults (id, timestamps)
        session.add(model)
        await session.flush()

        return DeployedStrategy(**model.to_dict())

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to deploy strategy {request.strategy_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to deploy strategy")


@router.get("/deployed/", response_model=List[DeployedStrategy])
async def list_deployed_strategies(
    current_user_id: str = Depends(get_user_id)
) -> List[DeployedStrategy]:
    """
    List deployed trading strategies.

    Args:
        current_user: Current authenticated user (optional)

    Returns:
        List of deployed strategies
    """
    # Try to return persisted deployments from DB when available
    try:
        async with get_session() as session:  # type: AsyncSession
            result = await session.execute(select(DeployedStrategyModel).order_by(DeployedStrategyModel.created_at.desc()))
            rows = result.scalars().all()
            return [DeployedStrategy(**r.to_dict()) for r in rows]
    except Exception:
        # Fall back to empty list if DB not available
        return []


@router.delete("/deployed/{deployment_id}")
async def undeploy_strategy(
    deployment_id: str,
    current_user_id: str = Depends(get_user_id)
):
    """
    Undeploy a trading strategy.

    Args:
        deployment_id: ID of the deployment to remove
        current_user: Current authenticated user (optional)
    """
    # Attempt to remove persisted deployment record
    try:
        uid = uuid.UUID(deployment_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid deployment id")

    try:
        async with get_session() as session:
            obj = await session.get(DeployedStrategyModel, uid)
            if not obj:
                raise HTTPException(status_code=404, detail="Deployment not found")
            await session.delete(obj)
            # commit handled by context manager
            return {"detail": "undeployed"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to undeploy {deployment_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to undeploy")