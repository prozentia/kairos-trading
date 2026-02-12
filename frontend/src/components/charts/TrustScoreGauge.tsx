import { useTheme } from "@/components/theme-provider";
import ReactApexChart from "react-apexcharts";
import type { ApexOptions } from "apexcharts";

interface TrustScoreGaugeProps {
  score?: number;
  chartHeight?: number;
}

function getTrustLevel(score: number): { label: string; color: string } {
  if (score < 40) return { label: "CRAWL", color: "#ef4444" };
  if (score < 65) return { label: "WALK", color: "#f59e0b" };
  if (score < 80) return { label: "RUN", color: "#3b82f6" };
  return { label: "SPRINT", color: "#22c55e" };
}

const TrustScoreGauge = ({ score = 46, chartHeight = 200 }: TrustScoreGaugeProps) => {
  const { theme } = useTheme();
  const isDark = theme === "dark" || (theme === "system" && window.matchMedia("(prefers-color-scheme: dark)").matches);
  const trust = getTrustLevel(score);

  const options: ApexOptions = {
    chart: {
      type: "radialBar",
      background: "transparent",
    },
    plotOptions: {
      radialBar: {
        startAngle: -135,
        endAngle: 135,
        hollow: { size: "65%" },
        track: {
          background: isDark ? "rgba(255,255,255,0.1)" : "#e5e7eb",
          strokeWidth: "100%",
        },
        dataLabels: {
          name: {
            show: true,
            fontSize: "14px",
            fontWeight: "600",
            color: trust.color,
            offsetY: -10,
          },
          value: {
            show: true,
            fontSize: "28px",
            fontWeight: "700",
            color: isDark ? "#e5e7eb" : "#1f2937",
            offsetY: 5,
            formatter: (val: number) => `${val}`,
          },
        },
      },
    },
    fill: {
      type: "gradient",
      gradient: {
        shade: "dark",
        type: "horizontal",
        shadeIntensity: 0.5,
        colorStops: [
          { offset: 0, color: "#ef4444", opacity: 1 },
          { offset: 40, color: "#f59e0b", opacity: 1 },
          { offset: 65, color: "#3b82f6", opacity: 1 },
          { offset: 100, color: "#22c55e", opacity: 1 },
        ],
      },
    },
    labels: [trust.label],
  };

  return (
    <ReactApexChart
      options={options}
      series={[score]}
      type="radialBar"
      height={chartHeight}
    />
  );
};

export default TrustScoreGauge;
