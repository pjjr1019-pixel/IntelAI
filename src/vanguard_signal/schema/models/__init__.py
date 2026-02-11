# Models package — import all tables so `Base.metadata` sees them.
from vanguard_signal.schema.models.ingestion import (
    SourceRegistry,
    RawIngestion,
    NormalizedEvent,
    NewsArticle,
)
from vanguard_signal.schema.models.signal import (
    SignalTimeSeries,
    AnomalyResult,
    SemanticCluster,
    SemanticClusterMember,
)
from vanguard_signal.schema.models.alert import (
    Alert,
    EvidenceChain,
    HistoricalAnalog,
    PostMortem,
    AnalystFeedback,
    BacktestRun,
    BacktestAlert,
    AlertEscalation,
    AlertSilence,
    AlertRule,
    AlertRuleTrigger,
    AlertRuleAnalytics,
    ReplaySession,
    ReplaySnapshot,
    ReplayDecision,
    ReplaySignal,
)
from vanguard_signal.schema.models.user import User
from vanguard_signal.schema.models.trend import (
    TrendSnapshot,
    TrendKeyword,
    TrendTimeSeries,
    TrendAlert,
    PredictionModel,
    PredictionResult,
)
from vanguard_signal.schema.models.report import (
    ScheduledReport,
    ReportTemplate,
)
from vanguard_signal.schema.models.trading import (
    Portfolio,
    Order,
    Position,
    RiskMetrics,
    MarketData,
)
from vanguard_signal.schema.models.narrative import (
    NarrativeCluster,
    NarrativeClusterArticle,
    NarrativeSaturation,
    NarrativeAlert,
)
from vanguard_signal.schema.models.simulation import (
    SimulationSession,
    SimulationOrder,
    SimulationPosition,
    SimulationResult,
    MarketCondition,
)
from vanguard_signal.schema.models.keyword_expansion import (
    KeywordRelationship,
    KeywordCluster,
    KeywordClusterMembership,
    KeywordExpansionCache,
)
from vanguard_signal.schema.models.risk_management import (
    RiskProfile,
    PositionSizeRule,
    StopLossRule,
    CircuitBreaker,
    RiskAlert,
    UserRiskMetrics,
    DrawdownLimit,
    DiversificationRule,
)

__all__ = [
    # Ingestion layer
    "SourceRegistry",
    "RawIngestion",
    "NormalizedEvent",
    # Signal layer
    "SignalTimeSeries",
    "AnomalyResult",
    "SemanticCluster",
    "SemanticClusterMember",
    # Alert layer
    "Alert",
    "EvidenceChain",
    "HistoricalAnalog",
    "PostMortem",
    "AnalystFeedback",
    "BacktestRun",
    "BacktestAlert",
    "AlertEscalation",
    "AlertSilence",
    "AlertRule",
    "AlertRuleTrigger",
    "AlertRuleAnalytics",
    "ReplaySession",
    "ReplaySnapshot",
    "ReplayDecision",
    "ReplaySignal",
    # Auth
    "User",
    # Trend layer
    "TrendSnapshot",
    "TrendKeyword",
    "TrendTimeSeries",
    "TrendAlert",
    "PredictionModel",
    "PredictionResult",
    # Report layer
    "ScheduledReport",
    "ReportTemplate",
    # Trading layer
    "Portfolio",
    "Order",
    "Position",
    "RiskMetrics",
    # Narrative layer
    "NarrativeCluster",
    "NarrativeClusterArticle",
    "NarrativeSaturation",
    "NarrativeAlert",
    # Simulation layer
    "SimulationSession",
    "SimulationOrder",
    "SimulationPosition",
    "SimulationResult",
    "MarketCondition",
    # Risk Management layer
    "RiskProfile",
    "PositionSizeRule",
    "StopLossRule",
    "CircuitBreaker",
    "RiskAlert",
    "UserRiskMetrics",
    "DrawdownLimit",
    "DiversificationRule",
    # Keyword Expansion layer
    "KeywordRelationship",
    "KeywordCluster",
    "KeywordClusterMembership",
    "KeywordExpansionCache",
]

# Deployed strategies (runtime deployments)
from vanguard_signal.schema.models.deployed_strategy import DeployedStrategy

__all__.append("DeployedStrategy")
