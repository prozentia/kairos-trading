import { useTheme } from "@/components/theme-provider";
import ReactApexChart from "react-apexcharts";
import type { ApexOptions } from "apexcharts";

interface PortfolioDonutProps {
  data?: Array<{ label: string; value: number }>;
  chartHeight?: number;
}

const PortfolioDonut = ({ data = [], chartHeight = 260 }: PortfolioDonutProps) => {
  const { theme } = useTheme();
  const isDark = theme === "dark" || (theme === "system" && window.matchMedia("(prefers-color-scheme: dark)").matches);

  // Demo data
  const chartData = data.length > 0
    ? data
    : [
        { label: "USDT", value: 65 },
        { label: "BTC", value: 20 },
        { label: "ETH", value: 10 },
        { label: "SOL", value: 5 },
      ];

  const series = chartData.map((d) => d.value);
  const labels = chartData.map((d) => d.label);

  const options: ApexOptions = {
    chart: {
      type: "donut",
      background: "transparent",
      foreColor: isDark ? "#e5e7eb" : "#374151",
    },
    labels,
    colors: ["#6366f1", "#f59e0b", "#3b82f6", "#10b981", "#ef4444"],
    legend: {
      position: "bottom",
      fontSize: "12px",
    },
    dataLabels: {
      enabled: true,
      formatter: (val: number) => `${val.toFixed(0)}%`,
    },
    plotOptions: {
      pie: {
        donut: {
          size: "65%",
          labels: {
            show: true,
            total: {
              show: true,
              label: "Total",
              fontSize: "14px",
              fontWeight: "600",
            },
          },
        },
      },
    },
    tooltip: { theme: isDark ? "dark" : "light" },
  };

  return (
    <ReactApexChart
      options={options}
      series={series}
      type="donut"
      height={chartHeight}
    />
  );
};

export default PortfolioDonut;
