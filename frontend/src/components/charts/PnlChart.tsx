import { useTheme } from "@/components/theme-provider";
import ReactApexChart from "react-apexcharts";
import type { ApexOptions } from "apexcharts";

interface PnlChartProps {
  data?: Array<{ date: string; pnl: number }>;
  chartHeight?: number;
}

const PnlChart = ({ data = [], chartHeight = 250 }: PnlChartProps) => {
  const { theme } = useTheme();
  const isDark = theme === "dark" || (theme === "system" && window.matchMedia("(prefers-color-scheme: dark)").matches);

  // Demo data if nothing provided
  const chartData = data.length > 0
    ? data
    : Array.from({ length: 30 }, (_, i) => ({
        date: new Date(Date.now() - (30 - i) * 86400000).toISOString().split("T")[0],
        pnl: +(Math.random() * 20 - 5 + i * 0.3).toFixed(2),
      }));

  const series: ApexAxisChartSeries = [{
    name: "P&L",
    data: chartData.map((d) => ({
      x: new Date(d.date).getTime(),
      y: d.pnl,
    })),
  }];

  const options: ApexOptions = {
    chart: {
      type: "area",
      height: chartHeight,
      toolbar: { show: false },
      background: "transparent",
      foreColor: isDark ? "#e5e7eb" : "#374151",
    },
    stroke: { curve: "smooth", width: 2 },
    fill: {
      type: "gradient",
      gradient: {
        shadeIntensity: 1,
        opacityFrom: 0.4,
        opacityTo: 0.05,
        stops: [0, 100],
      },
    },
    colors: ["#6366f1"],
    grid: {
      borderColor: isDark ? "rgba(255,255,255,0.1)" : "#e5e7eb",
      strokeDashArray: 3,
    },
    xaxis: {
      type: "datetime",
      labels: { style: { fontSize: "11px" } },
    },
    yaxis: {
      labels: {
        formatter: (val: number) => `$${val.toFixed(2)}`,
        style: { fontSize: "11px" },
      },
    },
    tooltip: {
      theme: isDark ? "dark" : "light",
      y: { formatter: (val: number) => `$${val.toFixed(2)}` },
    },
    dataLabels: { enabled: false },
  };

  return (
    <ReactApexChart
      options={options}
      series={series}
      type="area"
      height={chartHeight}
    />
  );
};

export default PnlChart;
