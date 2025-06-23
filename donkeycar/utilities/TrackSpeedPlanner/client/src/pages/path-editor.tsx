import { useState } from "react";
import { Route, Power } from "lucide-react";
import { PathDataPoint } from "@shared/schema";
import { FileUpload } from "@/components/file-upload";
import { PathCanvas } from "@/components/path-canvas";
import { SpeedControls } from "@/components/speed-controls";
import { Button } from "@/components/ui/button";
import { useToast } from "@/hooks/use-toast";
import { apiRequest } from "@/lib/queryClient";

export default function PathEditor() {
  const [pathData, setPathData] = useState<PathDataPoint[]>([]);
  const [selectedPointIndex, setSelectedPointIndex] = useState(-1);
  const [fileName, setFileName] = useState<string>("");
  const { toast } = useToast();

  const handleDataLoaded = (data: PathDataPoint[], loadedFileName: string) => {
    setPathData(data);
    setFileName(loadedFileName);
    setSelectedPointIndex(-1);
  };

  const handleShutdown = async () => {
    try {
      toast({
        title: "Shutting down server...",
        description: "The server will stop in a few seconds.",
      });

      await apiRequest('POST', '/api/shutdown');
    } catch (error) {
      // Expected error since server shuts down before response
      setTimeout(() => {
        window.location.href = 'about:blank';
      }, 2000);
    }
  };

  const handleSpeedChange = (index: number, newSpeed: number) => {
    const updatedData = [...pathData];
    updatedData[index] = { ...updatedData[index], speed: newSpeed };
    setPathData(updatedData);
  };

  const handlePointSelect = (index: number) => {
    setSelectedPointIndex(index);
    
    // Scroll to the corresponding speed control
    const speedControlsContainer = document.querySelector('.space-y-3');
    const controlElement = speedControlsContainer?.children[index] as HTMLElement;
    if (controlElement) {
      controlElement.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
  };



  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            <div className="flex items-center">
              <Route className="text-primary text-2xl mr-3 w-8 h-8" />
              <h1 className="text-xl font-semibold text-gray-900">Path Data Visualizer & Editor</h1>
            </div>
            <Button
              variant="outline"
              size="sm"
              onClick={handleShutdown}
              className="flex items-center gap-2 text-red-600 border-red-200 hover:bg-red-50 hover:border-red-300"
            >
              <Power className="w-4 h-4" />
              Exit
            </Button>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          
          {/* Left Column - File Upload and Visualization */}
          <div className="lg:col-span-2">
            <FileUpload onDataLoaded={handleDataLoaded} pathData={pathData} />
            <PathCanvas 
              pathData={pathData}
              selectedPointIndex={selectedPointIndex}
              onPointSelect={handlePointSelect}
            />
          </div>

          {/* Right Column - Speed Controls */}
          <div className="lg:col-span-1">
            <SpeedControls 
              pathData={pathData}
              selectedPointIndex={selectedPointIndex}
              onSpeedChange={handleSpeedChange}
              onPointSelect={handlePointSelect}
            />
          </div>
        </div>
      </div>
    </div>
  );
}
