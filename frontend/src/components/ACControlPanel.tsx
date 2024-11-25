import React, { useState, useEffect, useCallback } from "react";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Slider } from "@/components/ui/slider";
import axios from "axios";
import {
  AlertCircle,
  Power,
  ThermometerSun,
  Droplets,
  Zap,
} from "lucide-react";
import { Alert, AlertDescription } from "@/components/ui/alert";

interface ACStatus {
  currentTemperature: number;
  targetTemperature: number;
  humidity: number;
  powerUsage: number;
  electricityCost: number;
  power: boolean;
  namespaceIndex: number;
}

const ACControlPanel = () => {
  const [status, setStatus] = useState<ACStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [targetTemp, setTargetTemp] = useState(24);

  const fetchStatus = useCallback(async () => {
    try {
      const { data } = await axios.get<ACStatus>("/api/ac/status");
      setStatus(data);
      setError(null);
    } catch (err) {
      setError("Failed to fetch AC status");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchStatus();
    const interval = setInterval(fetchStatus, 1000);
    return () => clearInterval(interval);
  }, [fetchStatus]);

  const handlePowerToggle = async () => {
    try {
      await axios.post("/api/ac/power", { power: !status?.power });
      fetchStatus();
    } catch (err) {
      setError("Failed to toggle power");
    }
  };

  const handleTemperatureChange = async () => {
    try {
      await axios.post("/api/ac/temperature", { temperature: targetTemp });
      fetchStatus();
    } catch (err) {
      setError("Failed to update temperature");
    }
  };

  if (loading && !status) {
    return <div className="text-center p-4">Loading...</div>;
  }

  return (
    <Card className="w-full max-w-2xl mx-auto">
      <CardHeader>
        <CardTitle className="flex items-center justify-between">
          <span>Air Conditioner Control</span>
          <Button
            variant={status?.power ? "default" : "outline"}
            onClick={handlePowerToggle}
            className={`w-24 ${
              status?.power ? "bg-green-500 hover:bg-green-600" : ""
            }`}
          >
            <Power className="mr-2 h-4 w-4" />
            {status?.power ? "ON" : "OFF"}
          </Button>
        </CardTitle>
      </CardHeader>

      <CardContent className="space-y-6">
        {error && (
          <Alert variant="destructive">
            <AlertCircle className="h-4 w-4" />
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}

        <div className="grid grid-cols-2 gap-4">
          {/* Current Temperature */}
          <div className="p-4 bg-gray-50 rounded-lg">
            <div className="flex items-center gap-2 text-sm text-gray-500 mb-2">
              <ThermometerSun className="h-4 w-4" />
              <span>Current Temperature</span>
            </div>
            <div className="text-2xl font-bold">
              {status?.currentTemperature.toFixed(1)}°C
            </div>
          </div>

          {/* Humidity */}
          <div className="p-4 bg-gray-50 rounded-lg">
            <div className="flex items-center gap-2 text-sm text-gray-500 mb-2">
              <Droplets className="h-4 w-4" />
              <span>Humidity</span>
            </div>
            <div className="text-2xl font-bold">
              {status?.humidity.toFixed(1)}%
            </div>
          </div>

          {/* Power Usage */}
          <div className="p-4 bg-gray-50 rounded-lg">
            <div className="flex items-center gap-2 text-sm text-gray-500 mb-2">
              <Zap className="h-4 w-4" />
              <span>Power Usage</span>
            </div>
            <div className="text-2xl font-bold">
              {status?.powerUsage.toFixed(2)} kWh
            </div>
          </div>

          {/* Electricity Cost */}
          <div className="p-4 bg-gray-50 rounded-lg">
            <div className="flex items-center gap-2 text-sm text-gray-500 mb-2">
              <span className="font-bold">₩</span>
              <span>Electricity Cost</span>
            </div>
            <div className="text-2xl font-bold">
              {status?.electricityCost.toLocaleString()} KRW
            </div>
          </div>
        </div>

        {/* Temperature Control */}
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <span className="text-sm text-gray-500">Target Temperature</span>
            <span className="text-sm font-medium">{targetTemp}°C</span>
          </div>
          <div className="flex items-center gap-4">
            <Slider
              value={[targetTemp]}
              onValueChange={(values) => {
                // 슬라이더 값이 범위를 벗어나지 않도록
                const temp = Math.max(18, Math.min(30, values[0]));
                setTargetTemp(temp);
              }}
              min={18}
              max={30}
              step={0.5}
              className="flex-1"
            />
            <Button
              onClick={handleTemperatureChange}
              disabled={!status?.power || targetTemp < 18 || targetTemp > 30}
              className="w-24"
            >
              Set
            </Button>
          </div>
          {(targetTemp < 18 || targetTemp > 30) && (
            <p className="text-sm text-red-500">
              Temperature must be between 18°C and 30°C
            </p>
          )}
        </div>
      </CardContent>
    </Card>
  );
};

export default ACControlPanel;
