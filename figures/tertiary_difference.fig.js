const rows = JSON.parse(await loadText("build/tertiary_difference.json"));

// the pipeline's cohort order, which a plain sort would not recover
const cohorts = [
  "-1954", "1955-59", "1960-64", "1965-69", "1970-74",
  "1975-79", "1980-84", "1985-89", "1990-98",
];
const last = cohorts[cohorts.length - 1];
const austria = rows.filter((d) => d.country === "AT");
const others = rows.filter((d) => d.country !== "AT");

const spec = ({ document, width }) => ({
  document,
  width,
  marginRight: 74,
  marginBottom: 56,
  x: { label: "birth cohort", type: "point", domain: cohorts, tickRotate: -35 },
  y: {
    label: "women minus men, % holding a degree",
    percent: true,
    grid: true,
    domain: [-30, 30],
  },
  marks: [
    Plot.ruleY([0], { stroke: "#111827", strokeWidth: 1 }),
    Plot.lineY(others, {
      x: "cohort",
      y: "lead",
      z: "country",
      stroke: "#cbd5e1",
      strokeWidth: 1,
    }),
    Plot.lineY(austria, { x: "cohort", y: "lead", stroke: "#c2410c", strokeWidth: 2.2 }),
    Plot.dot(austria, { x: "cohort", y: "lead", fill: "#c2410c", r: 3.5 }),
    Plot.text(austria.filter((d) => d.cohort === last), {
      x: "cohort",
      y: "lead",
      text: () => "Austria",
      fill: "#c2410c",
      textAnchor: "start",
      dx: 8,
    }),
  ],
});
