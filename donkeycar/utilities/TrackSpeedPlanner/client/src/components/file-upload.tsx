import { useState, useRef } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Upload, FileText, Download } from "lucide-react";
import { useToast } from "@/hooks/use-toast";
import { PathDataPoint } from "@shared/schema";
import { parseCSV, exportToCSV, downloadCSV } from "@/lib/csv-utils";

interface FileUploadProps {
  onDataLoaded: (data: PathDataPoint[], fileName: string) => void;
  pathData: PathDataPoint[];
}

export function FileUpload({ onDataLoaded, pathData }: FileUploadProps) {
  const [isDragging, setIsDragging] = useState(false);
  const [uploadedFile, setUploadedFile] = useState<string | null>(null);
  const [pointCount, setPointCount] = useState(0);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const { toast } = useToast();

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    const files = e.dataTransfer.files;
    if (files.length > 0) {
      processFile(files[0]);
    }
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      processFile(file);
    }
  };

  const processFile = (file: File) => {
    if (!file.name.toLowerCase().endsWith('.csv')) {
      toast({
        title: "Error",
        description: "Please upload a CSV file.",
        variant: "destructive",
      });
      return;
    }

    const reader = new FileReader();
    reader.onload = function(e) {
      try {
        const csv = e.target?.result as string;
        const pathData = parseCSV(csv);
        
        if (pathData.length > 0) {
          setUploadedFile(file.name);
          setPointCount(pathData.length);
          onDataLoaded(pathData, file.name);
          toast({
            title: "Success",
            description: `Loaded ${pathData.length} data points from ${file.name}`,
          });
        } else {
          toast({
            title: "Error",
            description: "No valid data points found in the CSV file.",
            variant: "destructive",
          });
        }
      } catch (error) {
        toast({
          title: "Error",
          description: "Failed to parse CSV file. Please check the format.",
          variant: "destructive",
        });
      }
    };
    reader.readAsText(file);
  };

  const handleExportCSV = () => {
    if (!pathData || pathData.length === 0) {
      toast({
        title: "Error",
        description: "No data to export. Please upload a file first.",
        variant: "destructive",
      });
      return;
    }

    const csvContent = exportToCSV(pathData);
    downloadCSV(csvContent);
    
    toast({
      title: "Success",
      description: "CSV file has been downloaded successfully!",
    });
  };

  return (
    <Card className="bg-white">
      <CardContent className="p-6">
        <div className="mb-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-2">Upload Path Data</h2>
          <p className="text-sm text-gray-600">Upload a CSV file with x,y,speed format to visualize and edit the path.</p>
        </div>
        
        <div 
          className={`border-2 border-dashed rounded-lg p-6 text-center transition-colors cursor-pointer ${
            isDragging 
              ? 'border-primary bg-blue-50' 
              : 'border-gray-300 hover:border-primary hover:bg-blue-50'
          }`}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
          onClick={() => fileInputRef.current?.click()}
        >
          <Upload className="mx-auto text-gray-400 mb-3 w-8 h-8" />
          <p className="font-medium text-gray-700 mb-1">Drop your CSV file here or click to browse</p>
          <p className="text-sm text-gray-500">Supports CSV files with x,y,speed format</p>
          <input 
            ref={fileInputRef}
            type="file" 
            accept=".csv" 
            className="hidden"
            onChange={handleFileSelect}
          />
        </div>
        
        {uploadedFile && (
          <div className="mt-4 p-4 bg-blue-50 rounded-lg">
            <div className="flex items-center justify-between">
              <div className="flex items-center">
                <FileText className="text-primary mr-3 w-5 h-5" />
                <div>
                  <p className="font-medium text-gray-900">{uploadedFile}</p>
                  <p className="text-sm text-gray-600">{pointCount} data points loaded</p>
                </div>
              </div>
              <Button 
                onClick={handleExportCSV}
                disabled={!pathData || pathData.length === 0}
                className="bg-green-600 hover:bg-green-700 text-white"
              >
                <Download className="mr-2 w-4 h-4" />
                Export CSV
              </Button>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
