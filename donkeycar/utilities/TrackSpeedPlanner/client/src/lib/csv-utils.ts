import { PathDataPoint } from "@shared/schema";

export function parseCSV(csvContent: string): PathDataPoint[] {
  const lines = csvContent.trim().split('\n');
  const pathData: PathDataPoint[] = [];

  lines.forEach((line, lineIndex) => {
    const parts = line.split(',').map(part => part.trim());
    if (parts.length >= 3) {
      const x = parseFloat(parts[0]);
      const y = parseFloat(parts[1]);
      const speed = parseFloat(parts[2]);
      
      if (!isNaN(x) && !isNaN(y) && !isNaN(speed)) {
        pathData.push({ x, y, speed, index: pathData.length });
      }
    }
  });

  return pathData;
}

export function exportToCSV(pathData: PathDataPoint[]): string {
  return pathData.map(point => 
    `${point.x}, ${point.y}, ${point.speed.toFixed(2)}`
  ).join('\n');
}

export function downloadCSV(content: string, filename: string = 'modified_path_data.csv'): void {
  const blob = new Blob([content], { type: 'text/csv' });
  const url = window.URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  link.click();
  window.URL.revokeObjectURL(url);
}

export function generateSpeedOptions(currentSpeed: number): Array<{ value: number; label: string }> {
  const options = [];
  for (let i = 1; i <= 10; i++) {
    const speed = i / 10;
    options.push({
      value: speed,
      label: speed.toFixed(1)
    });
  }
  return options;
}
