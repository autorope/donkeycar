import { Card, CardContent } from "@/components/ui/card";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { PathDataPoint } from "@shared/schema";
import { generateSpeedOptions } from "@/lib/csv-utils";
import { Upload } from "lucide-react";

interface SpeedControlsProps {
  pathData: PathDataPoint[];
  selectedPointIndex: number;
  onSpeedChange: (index: number, newSpeed: number) => void;
  onPointSelect: (index: number) => void;
}

export function SpeedControls({ pathData, selectedPointIndex, onSpeedChange, onPointSelect }: SpeedControlsProps) {
  const handleSpeedChange = (index: number, value: string) => {
    const newSpeed = parseFloat(value);
    onSpeedChange(index, newSpeed);
  };

  const handleControlClick = (index: number) => {
    onPointSelect(index);
  };

  if (pathData.length === 0) {
    return (
      <Card className="bg-white sticky top-8">
        <CardContent className="p-6">
          <div className="mb-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-2">Speed Controls</h2>
            <p className="text-sm text-gray-600">Adjust the speed value for each point in your path.</p>
          </div>
          
          <div className="text-center py-8 text-gray-500">
            <Upload className="mx-auto text-3xl mb-3 w-12 h-12" />
            <p>Upload a file to see speed controls</p>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="bg-white sticky top-8">
      <CardContent className="p-6">
        <div className="mb-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-2">Speed Controls</h2>
          <p className="text-sm text-gray-600">Adjust the speed value for each point in your path.</p>
        </div>
        
        <div className="space-y-3 max-h-96 overflow-y-auto">
          {pathData.map((point, index) => (
            <div 
              key={index}
              className={`flex items-center justify-between p-3 rounded-lg transition-colors cursor-pointer ${
                index === selectedPointIndex 
                  ? 'bg-blue-100 border border-blue-300' 
                  : 'bg-gray-50 hover:bg-gray-100'
              }`}
              onClick={() => handleControlClick(index)}
            >
              <div className="flex items-center">
                <span className="w-8 h-8 bg-primary text-white rounded-full flex items-center justify-center text-sm font-medium mr-3">
                  {index + 1}
                </span>
                <div className="text-sm">
                  <div className="font-medium text-gray-900">Point {index + 1}</div>
                  <div className="text-gray-600 font-mono">({point.x.toFixed(3)}, {point.y.toFixed(3)})</div>
                  <div className="text-xs text-gray-500">Speed: {point.speed.toFixed(1)}</div>
                </div>
              </div>
              <Select 
                value={point.speed.toFixed(1)} 
                onValueChange={(value) => handleSpeedChange(index, value)}
              >
                <SelectTrigger className="w-20">
                  <SelectValue placeholder={point.speed.toFixed(1)} />
                </SelectTrigger>
                <SelectContent>
                  {generateSpeedOptions(point.speed).map((option) => (
                    <SelectItem key={option.value} value={option.value.toString()}>
                      {option.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          ))}
        </div>
        
        <div className="mt-6 pt-6 border-t border-gray-200">
          <div className="flex items-center justify-between text-sm">
            <span className="text-gray-600">Total Points:</span>
            <span className="font-medium text-gray-900">{pathData.length}</span>
          </div>
          <div className="flex items-center justify-between text-sm mt-2">
            <span className="text-gray-600">Speed Range:</span>
            <span className="font-medium text-gray-900">0.1 - 1.0</span>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
