import type { GetServerSideProps, NextPage } from "next";
import useSWR from "swr";

type PortKpis = {
  containersInYard: number;
  avgDwellHours: number;
  customsPendingCount: number;
  gateThroughputPerHour: number;
};

const fetcher = (url: string) => fetch(url).then((r) => r.json());

const Dashboard: NextPage<{ initial: PortKpis }> = ({ initial }) => {
  const { data } = useSWR<PortKpis>("/api/kpis", fetcher, {
    fallbackData: initial,
    refreshInterval: 30_000,
  });

  return (
    <main style={{ padding: 24, fontFamily: "Inter, system-ui" }}>
      <h1>Oxagon Port — Live Operations</h1>
      <section style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 16 }}>
        <Kpi label="Containers in yard" value={data?.containersInYard.toLocaleString()} />
        <Kpi label="Avg dwell (h)" value={data?.avgDwellHours.toFixed(1)} />
        <Kpi label="Customs pending" value={data?.customsPendingCount.toLocaleString()} />
        <Kpi label="Gate throughput / hr" value={data?.gateThroughputPerHour.toFixed(0)} />
      </section>
    </main>
  );
};

function Kpi({ label, value }: { label: string; value?: string }) {
  return (
    <div style={{ padding: 16, borderRadius: 12, background: "#0b1220", color: "#fff" }}>
      <div style={{ opacity: 0.7, fontSize: 12, textTransform: "uppercase" }}>{label}</div>
      <div style={{ fontSize: 32, fontWeight: 700 }}>{value ?? "—"}</div>
    </div>
  );
}

export const getServerSideProps: GetServerSideProps = async () => {
  const initial: PortKpis = {
    containersInYard: 11842,
    avgDwellHours: 58.4,
    customsPendingCount: 42,
    gateThroughputPerHour: 94,
  };
  return { props: { initial } };
};

export default Dashboard;
