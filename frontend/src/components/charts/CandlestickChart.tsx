import type { Candle } from "@/types";
import { useTheme } from "@/components/theme-provider";
import { useEffect, useState } from "react";
import ReactApexChart from "react-apexcharts";
import type { ApexOptions } from "apexcharts";

interface CandlestickChartProps {
  candles?: Candle[];
  chartHeight?: number;
}

const CandlestickChart = ({ candles = [], chartHeight = 350 }: CandlestickChartProps) => {
  const { theme } = useTheme();
  const isDark = theme === "dark" || (theme === "system" && window.matchMedia("(prefers-color-scheme: dark)").matches);
  const [series, setSeries] = useState<ApexAxisChartSeries>([]);

  useEffect(() => {
    if (candles.length > 0) {
      setSeries([{
        name: "Price",
        data: candles.map((c) => ({
          x: new Date(c.timestamp).getTime(),
          y: [c.open, c.high, c.low, c.close],
        })),
      }]);
    } else {
      // Demo data when no real candles available
      const now = Date.now();
      const demoData = Array.from({ length: 60 }, (_, i) => {
        const base = 67000 + Math.sin(i / 5) * 500 + Math.random() * 200;
        const open = base;
        const close = base + (Math.random() - 0.48) * 300;
        const high = Math.max(open, close) + Math.random() * 150;
        const low = Math.min(open, close) - Math.random() * 150;
        return {
          x: now - (60 - i) * 5 * 60 * 1000,
          y: [+open.toFixed(2), +high.toFixed(2), +low.toFixed(2), +close.toFixed(2)],
        };
      });
      setSeries([{ name: "BTC/USDT", data: demoData }]);
    }
  }, [candles]);

  const options: ApexOptions = {
    chart: {
      type: "candlestick",
      height: chartHeight,
      toolbar: { show: true },
      background: "transparent",
      foreColor: isDark ? "#e5e7eb" : "#374151",
    },
    grid: {
      borderColor: isDark ? "rgba(255,255,255,0.1)" : "#e5e7eb",
      strokeDashArray: 3,
    },
    xaxis: {
      type: "datetime",
      labels: { style: { fontSize: "11px" } },
    },
    yaxis: {
      tooltip: { enabled: true },
      labels: {
        formatter: (val: number) => `$${val.toLocaleString()}`,
        style: { fontSize: "11px" },
      },
    },
    plotOptions: {
      candlestick: {
        colors: {
          upward: "#22c55e",
          downward: "#ef4444",
        },
        wick: { useFillColor: true },
      },
    },
    tooltip: {
      theme: isDark ? "dark" : "light",
    },
    theme: { mode: isDark ? "dark" : "light" },
  };

  return (
    <div className="w-full">
      <ReactApexChart
        options={options}
        series={series}
        type="candlestick"
        height={chartHeight}
      />
    </div>
  );
};

export default CandlestickChart;
