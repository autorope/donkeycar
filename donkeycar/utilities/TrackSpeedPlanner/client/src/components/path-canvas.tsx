import { useEffect, useRef, useState } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { PathDataPoint } from "@shared/schema";

interface PathCanvasProps {
  pathData: PathDataPoint[];
  selectedPointIndex: number;
  onPointSelect: (index: number) => void;
}

interface CanvasBounds {
  minX: number;
  maxX: number;
  minY: number;
  maxY: number;
}

interface CanvasTransform {
  scaleX: number;
  scaleY: number;
  offsetX: number;
  offsetY: number;
}

export function PathCanvas({ pathData, selectedPointIndex, onPointSelect }: PathCanvasProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [coordinates, setCoordinates] = useState<string>("Click a point to view coordinates");
  const [isHovering, setIsHovering] = useState(false);

  useEffect(() => {
    drawPath();
  }, [pathData, selectedPointIndex]);

  useEffect(() => {
    const handleResize = () => {
      if (pathData.length > 0) {
        drawPath();
      }
    };

    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, [pathData]);

  const calculateBounds = (): CanvasBounds => {
    if (pathData.length === 0) {
      return { minX: 0, maxX: 1, minY: 0, maxY: 1 };
    }

    const xs = pathData.map(p => p.x);
    const ys = pathData.map(p => p.y);
    
    return {
      minX: Math.min(...xs),
      maxX: Math.max(...xs),
      minY: Math.min(...ys),
      maxY: Math.max(...ys)
    };
  };

  const calculateCanvasTransform = (bounds: CanvasBounds, canvas: HTMLCanvasElement): CanvasTransform => {
    const padding = 40;
    const dataWidth = bounds.maxX - bounds.minX;
    const dataHeight = bounds.maxY - bounds.minY;
    
    const scaleX = (canvas.width - 2 * padding) / (dataWidth || 1);
    const scaleY = (canvas.height - 2 * padding) / (dataHeight || 1);
    
    return {
      scaleX,
      scaleY,
      offsetX: padding,
      offsetY: padding
    };
  };

  const worldToCanvas = (point: PathDataPoint, bounds: CanvasBounds, transform: CanvasTransform, canvas: HTMLCanvasElement) => {
    const canvasX = (point.x - bounds.minX) * transform.scaleX + transform.offsetX;
    const canvasY = canvas.height - ((point.y - bounds.minY) * transform.scaleY + transform.offsetY);
    return { x: canvasX, y: canvasY };
  };

  const drawGrid = (ctx: CanvasRenderingContext2D, bounds: CanvasBounds, transform: CanvasTransform, canvas: HTMLCanvasElement) => {
    ctx.strokeStyle = '#e5e7eb';
    ctx.lineWidth = 1;
    
    const gridLines = 5;
    
    // Vertical grid lines
    for (let i = 0; i <= gridLines; i++) {
      const x = transform.offsetX + (canvas.width - 2 * transform.offsetX) * i / gridLines;
      ctx.beginPath();
      ctx.moveTo(x, transform.offsetY);
      ctx.lineTo(x, canvas.height - transform.offsetY);
      ctx.stroke();
    }
    
    // Horizontal grid lines
    for (let i = 0; i <= gridLines; i++) {
      const y = transform.offsetY + (canvas.height - 2 * transform.offsetY) * i / gridLines;
      ctx.beginPath();
      ctx.moveTo(transform.offsetX, y);
      ctx.lineTo(canvas.width - transform.offsetX, y);
      ctx.stroke();
    }
  };

  const drawAxesLabels = (ctx: CanvasRenderingContext2D, bounds: CanvasBounds, transform: CanvasTransform, canvas: HTMLCanvasElement) => {
    ctx.fillStyle = '#6b7280';
    ctx.font = '12px Inter, sans-serif';
    ctx.textAlign = 'center';
    
    // X-axis labels
    for (let i = 0; i <= 5; i++) {
      const x = transform.offsetX + (canvas.width - 2 * transform.offsetX) * i / 5;
      const value = bounds.minX + (bounds.maxX - bounds.minX) * i / 5;
      ctx.fillText(value.toFixed(2), x, canvas.height - 10);
    }
    
    // Y-axis labels
    ctx.textAlign = 'right';
    for (let i = 0; i <= 5; i++) {
      const y = transform.offsetY + (canvas.height - 2 * transform.offsetY) * i / 5;
      const value = bounds.maxY - (bounds.maxY - bounds.minY) * i / 5;
      ctx.fillText(value.toFixed(2), transform.offsetX - 10, y + 4);
    }
  };

  const drawPath = () => {
    const canvas = canvasRef.current;
    if (!canvas || pathData.length === 0) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    // Set canvas size
    const container = canvas.parentElement;
    if (container) {
      const rect = container.getBoundingClientRect();
      canvas.width = rect.width - 32; // Account for padding
      canvas.height = 400;
    }

    // Clear canvas
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    const bounds = calculateBounds();
    const transform = calculateCanvasTransform(bounds, canvas);

    // Draw grid
    drawGrid(ctx, bounds, transform, canvas);

    // Draw path lines
    ctx.strokeStyle = '#3b82f6';
    ctx.lineWidth = 2;
    ctx.beginPath();
    
    pathData.forEach((point, index) => {
      const canvasPoint = worldToCanvas(point, bounds, transform, canvas);
      
      if (index === 0) {
        ctx.moveTo(canvasPoint.x, canvasPoint.y);
      } else {
        ctx.lineTo(canvasPoint.x, canvasPoint.y);
      }
    });
    ctx.stroke();

    // Draw points
    pathData.forEach((point, index) => {
      const canvasPoint = worldToCanvas(point, bounds, transform, canvas);
      
      // Point circle
      ctx.fillStyle = index === selectedPointIndex ? '#ef4444' : '#2563eb';
      ctx.beginPath();
      ctx.arc(canvasPoint.x, canvasPoint.y, index === selectedPointIndex ? 6 : 4, 0, 2 * Math.PI);
      ctx.fill();
      
      // White border
      ctx.strokeStyle = '#ffffff';
      ctx.lineWidth = 1;
      ctx.stroke();
    });

    // Draw axes labels
    drawAxesLabels(ctx, bounds, transform, canvas);
  };

  const handleCanvasClick = (e: React.MouseEvent<HTMLCanvasElement>) => {
    const canvas = canvasRef.current;
    if (!canvas || pathData.length === 0) return;

    const rect = canvas.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;
    
    const bounds = calculateBounds();
    const transform = calculateCanvasTransform(bounds, canvas);
    
    // Find closest point
    let closestIndex = -1;
    let closestDistance = Infinity;
    
    pathData.forEach((point, index) => {
      const canvasPoint = worldToCanvas(point, bounds, transform, canvas);
      const distance = Math.sqrt((x - canvasPoint.x) ** 2 + (y - canvasPoint.y) ** 2);
      
      if (distance < 15 && distance < closestDistance) {
        closestDistance = distance;
        closestIndex = index;
      }
    });
    
    if (closestIndex !== -1) {
      const point = pathData[closestIndex];
      setCoordinates(`Point ${closestIndex + 1}: (${point.x.toFixed(3)}, ${point.y.toFixed(3)}) Speed: ${point.speed.toFixed(1)}`);
      onPointSelect(closestIndex);
    }
  };

  const handleCanvasHover = (e: React.MouseEvent<HTMLCanvasElement>) => {
    const canvas = canvasRef.current;
    if (!canvas || pathData.length === 0) return;

    const rect = canvas.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;
    
    const bounds = calculateBounds();
    const transform = calculateCanvasTransform(bounds, canvas);
    
    let hoveringPoint = false;
    
    pathData.forEach((point) => {
      const canvasPoint = worldToCanvas(point, bounds, transform, canvas);
      const distance = Math.sqrt((x - canvasPoint.x) ** 2 + (y - canvasPoint.y) ** 2);
      
      if (distance < 15) {
        hoveringPoint = true;
      }
    });
    
    setIsHovering(hoveringPoint);
  };

  return (
    <Card className="bg-white mt-6">
      <CardContent className="p-6">
        <div className="mb-4">
          <h2 className="text-lg font-semibold text-gray-900 mb-2">Path Visualization</h2>
          <p className="text-sm text-gray-600">Interactive plot showing your path data. Click points to edit their speed.</p>
        </div>
        
        <div className="bg-gray-50 rounded-lg p-4 mb-4">
          <canvas 
            ref={canvasRef}
            className={`w-full border border-gray-200 rounded bg-white ${isHovering ? 'cursor-pointer' : 'cursor-crosshair'}`}
            onClick={handleCanvasClick}
            onMouseMove={handleCanvasHover}
          />
        </div>
        
        <div className="flex items-center justify-between text-sm text-gray-600">
          <div className="flex items-center space-x-4">
            <div className="flex items-center">
              <div className="w-3 h-3 bg-primary rounded-full mr-2"></div>
              <span>Path points</span>
            </div>
            <div className="flex items-center">
              <div className="w-3 h-3 bg-red-500 rounded-full mr-2"></div>
              <span>Selected point</span>
            </div>
          </div>
          <div className="font-mono">
            {coordinates}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
