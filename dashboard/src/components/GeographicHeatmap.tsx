'use client';

import { useState, useEffect } from 'react';
import { MapPin, Globe, TrendingUp, Users } from 'lucide-react';

interface GeoData {
  country: string;
  countryCode: string;
  value: number;
  trend: 'up' | 'down' | 'stable';
  rank: number;
}

interface GeographicHeatmapProps {
  data: GeoData[];
  title?: string;
  height?: number;
  onCountryClick?: (countryCode: string) => void;
}

export default function GeographicHeatmap({
  data,
  title = 'Geographic Trend Distribution',
  height = 400,
  onCountryClick,
}: GeographicHeatmapProps) {
  const [selectedCountry, setSelectedCountry] = useState<string | null>(null);
  const [hoveredCountry, setHoveredCountry] = useState<string | null>(null);

  // Simple world map coordinates for major countries (simplified representation)
  const countryCoordinates: Record<string, { x: number; y: number; name: string }> = {
    'US': { x: 15, y: 35, name: 'United States' },
    'GB': { x: 48, y: 25, name: 'United Kingdom' },
    'DE': { x: 52, y: 28, name: 'Germany' },
    'FR': { x: 50, y: 32, name: 'France' },
    'JP': { x: 85, y: 35, name: 'Japan' },
    'CA': { x: 12, y: 25, name: 'Canada' },
    'AU': { x: 80, y: 75, name: 'Australia' },
    'IN': { x: 68, y: 50, name: 'India' },
    'BR': { x: 25, y: 65, name: 'Brazil' },
    'CN': { x: 75, y: 40, name: 'China' },
    'RU': { x: 60, y: 20, name: 'Russia' },
    'KR': { x: 82, y: 38, name: 'South Korea' },
    'MX': { x: 10, y: 45, name: 'Mexico' },
    'IT': { x: 53, y: 35, name: 'Italy' },
    'ES': { x: 48, y: 38, name: 'Spain' },
    'NL': { x: 51, y: 27, name: 'Netherlands' },
    'SE': { x: 53, y: 18, name: 'Sweden' },
    'NO': { x: 52, y: 15, name: 'Norway' },
    'DK': { x: 52, y: 22, name: 'Denmark' },
    'FI': { x: 55, y: 12, name: 'Finland' },
  };

  const getValueColor = (value: number, maxValue: number) => {
    const intensity = value / maxValue;
    if (intensity > 0.8) return 'bg-red-500';
    if (intensity > 0.6) return 'bg-orange-500';
    if (intensity > 0.4) return 'bg-yellow-500';
    if (intensity > 0.2) return 'bg-green-500';
    return 'bg-blue-500';
  };

  const getTrendColor = (trend: 'up' | 'down' | 'stable') => {
    switch (trend) {
      case 'up': return 'text-green-400';
      case 'down': return 'text-red-400';
      case 'stable': return 'text-gray-400';
    }
  };

  const getTrendIcon = (trend: 'up' | 'down' | 'stable') => {
    switch (trend) {
      case 'up': return <TrendingUp className="w-3 h-3" />;
      case 'down': return <TrendingUp className="w-3 h-3 rotate-180" />;
      case 'stable': return <div className="w-3 h-0.5 bg-current rounded" />;
    }
  };

  const maxValue = Math.max(...data.map(d => d.value));

  const handleCountryClick = (countryCode: string) => {
    setSelectedCountry(countryCode);
    onCountryClick?.(countryCode);
  };

  const selectedCountryData = selectedCountry ? data.find(d => d.countryCode === selectedCountry) : null;

  return (
    <div className="bg-surface-2/50 rounded-lg p-4">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-medium flex items-center gap-2">
          <Globe className="w-5 h-5" />
          {title}
        </h3>

        <div className="flex items-center gap-4 text-xs text-muted-foreground">
          <div className="flex items-center gap-1">
            <div className="w-3 h-3 bg-red-500 rounded"></div>
            <span>High</span>
          </div>
          <div className="flex items-center gap-1">
            <div className="w-3 h-3 bg-orange-500 rounded"></div>
            <span>Medium</span>
          </div>
          <div className="flex items-center gap-1">
            <div className="w-3 h-3 bg-green-500 rounded"></div>
            <span>Low</span>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* World Map Visualization */}
        <div className="lg:col-span-2">
          <div
            className="relative bg-surface-1 rounded-lg border border-white/[0.06] overflow-hidden"
            style={{ height: `${height}px` }}
          >
            {/* Simplified world map background */}
            <svg
              viewBox="0 0 100 100"
              className="w-full h-full"
              style={{ background: 'linear-gradient(135deg, #1f2937 0%, #111827 100%)' }}
            >
              {/* Simplified continents */}
              <path
                d="M10,20 Q15,15 25,18 Q35,20 40,25 Q38,35 30,40 Q20,38 15,30 Z"
                fill="#374151"
                opacity="0.3"
              />
              <path
                d="M45,15 Q55,12 65,18 Q70,25 68,35 Q60,40 50,38 Q45,30 45,15 Z"
                fill="#374151"
                opacity="0.3"
              />
              <path
                d="M75,20 Q85,18 90,25 Q88,35 80,40 Q70,38 75,20 Z"
                fill="#374151"
                opacity="0.3"
              />
              <path
                d="M15,45 Q25,42 35,48 Q40,55 38,65 Q30,70 20,68 Q15,60 15,45 Z"
                fill="#374151"
                opacity="0.3"
              />

              {/* Country markers */}
              {data.map((country) => {
                const coords = countryCoordinates[country.countryCode];
                if (!coords) return null;

                const size = Math.max(2, Math.min(8, (country.value / maxValue) * 6 + 2));
                const isHovered = hoveredCountry === country.countryCode;
                const isSelected = selectedCountry === country.countryCode;

                return (
                  <g key={country.countryCode}>
                    {/* Country circle */}
                    <circle
                      cx={coords.x}
                      cy={coords.y}
                      r={isHovered || isSelected ? size + 1 : size}
                      className={`${getValueColor(country.value, maxValue)} transition-all duration-200 cursor-pointer hover:opacity-80`}
                      onMouseEnter={() => setHoveredCountry(country.countryCode)}
                      onMouseLeave={() => setHoveredCountry(null)}
                      onClick={() => handleCountryClick(country.countryCode)}
                    />

                    {/* Trend indicator */}
                    <circle
                      cx={coords.x + size + 1}
                      cy={coords.y - size - 1}
                      r="1.5"
                      className={`${getTrendColor(country.trend)} fill-current`}
                    />

                    {/* Rank number for top countries */}
                    {country.rank <= 5 && (
                      <text
                        x={coords.x}
                        y={coords.y + size + 4}
                        textAnchor="middle"
                        className="text-xs fill-white font-medium"
                        style={{ fontSize: '3px' }}
                      >
                        #{country.rank}
                      </text>
                    )}
                  </g>
                );
              })}
            </svg>

            {/* Tooltip */}
            {hoveredCountry && (() => {
              const countryData = data.find(d => d.countryCode === hoveredCountry);
              const coords = countryCoordinates[hoveredCountry];
              if (!countryData || !coords) return null;

              return (
                <div
                  className="absolute bg-surface-2 border border-white/[0.06] rounded-lg p-2 text-xs pointer-events-none z-10"
                  style={{
                    left: `${(coords.x / 100) * 100}%`,
                    top: `${(coords.y / 100) * 100}%`,
                    transform: 'translate(-50%, -120%)',
                  }}
                >
                  <div className="font-medium">{countryData.country}</div>
                  <div className="flex items-center gap-2 mt-1">
                    <span>Value: {countryData.value.toFixed(1)}</span>
                    <span className={`flex items-center gap-1 ${getTrendColor(countryData.trend)}`}>
                      {getTrendIcon(countryData.trend)}
                      Rank #{countryData.rank}
                    </span>
                  </div>
                </div>
              );
            })()}
          </div>
        </div>

        {/* Country List & Details */}
        <div className="space-y-4">
          {/* Top Countries List */}
          <div>
            <h4 className="font-medium mb-3 flex items-center gap-2">
              <Users className="w-4 h-4" />
              Top Countries
            </h4>
            <div className="space-y-2 max-h-48 overflow-y-auto">
              {data
                .sort((a, b) => b.value - a.value)
                .slice(0, 10)
                .map((country) => (
                  <div
                    key={country.countryCode}
                    className={`flex items-center justify-between p-2 rounded cursor-pointer transition-colors ${
                      selectedCountry === country.countryCode ? 'bg-blue-500/20' : 'hover:bg-surface-1'
                    }`}
                    onClick={() => handleCountryClick(country.countryCode)}
                  >
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-medium w-6">#{country.rank}</span>
                      <span className="text-sm">{country.country}</span>
                      <div className={`flex items-center ${getTrendColor(country.trend)}`}>
                        {getTrendIcon(country.trend)}
                      </div>
                    </div>
                    <span className="text-sm font-medium">{country.value.toFixed(1)}</span>
                  </div>
                ))}
            </div>
          </div>

          {/* Selected Country Details */}
          {selectedCountryData && (
            <div className="bg-surface-1 rounded-lg p-3">
              <h4 className="font-medium mb-2 flex items-center gap-2">
                <MapPin className="w-4 h-4" />
                {selectedCountryData.country}
              </h4>
              <div className="space-y-1 text-sm">
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Value:</span>
                  <span className="font-medium">{selectedCountryData.value.toFixed(1)}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Rank:</span>
                  <span className="font-medium">#{selectedCountryData.rank}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Trend:</span>
                  <span className={`flex items-center gap-1 font-medium ${getTrendColor(selectedCountryData.trend)}`}>
                    {getTrendIcon(selectedCountryData.trend)}
                    {selectedCountryData.trend}
                  </span>
                </div>
              </div>
            </div>
          )}

          {/* Statistics */}
          <div className="bg-surface-1 rounded-lg p-3">
            <h4 className="font-medium mb-2">Statistics</h4>
            <div className="space-y-1 text-sm">
              <div className="flex justify-between">
                <span className="text-muted-foreground">Countries:</span>
                <span className="font-medium">{data.length}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Avg Value:</span>
                <span className="font-medium">
                  {(data.reduce((sum, d) => sum + d.value, 0) / data.length).toFixed(1)}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Max Value:</span>
                <span className="font-medium">{maxValue.toFixed(1)}</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}