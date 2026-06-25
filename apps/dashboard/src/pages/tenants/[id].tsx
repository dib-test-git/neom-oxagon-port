import type { GetServerSideProps, NextPage } from "next";

type TenantDetail = {
  id: string;
  displayName: string;
  commercialRegistrationNumber: string;
  activeShipments: number;
  monthToDateDwellHours: number;
  customsHealth: "GREEN" | "AMBER" | "RED";
};

const TenantPage: NextPage<{ tenant: TenantDetail }> = ({ tenant }) => (
  <main style={{ padding: 24, fontFamily: "Inter, system-ui" }}>
    <h1>{tenant.displayName}</h1>
    <p style={{ opacity: 0.6 }}>CR: {tenant.commercialRegistrationNumber}</p>
    <ul>
      <li>Active shipments: {tenant.activeShipments}</li>
      <li>MTD dwell (h): {tenant.monthToDateDwellHours.toFixed(1)}</li>
      <li>Customs health: {tenant.customsHealth}</li>
    </ul>
  </main>
);

export const getServerSideProps: GetServerSideProps = async ({ params }) => {
  const id = String(params?.id);
  const tenant: TenantDetail = {
    id,
    displayName: id === "oxagon-terminals" ? "Oxagon Terminals" : id,
    commercialRegistrationNumber: "2050-OXG-0042",
    activeShipments: 318,
    monthToDateDwellHours: 61.7,
    customsHealth: "GREEN",
  };
  return { props: { tenant } };
};

export default TenantPage;
