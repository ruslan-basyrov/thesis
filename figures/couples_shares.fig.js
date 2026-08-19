const brand = yaml.load(await loadText("_extensions/ruslan-basyrov/acuity/_brand.yml"));
const rows = JSON.parse(await loadText("build/couples_shares.json"));

// the order as in the shared source data
const levels = ["compulsory", "apprenticeship", "Matura", "tertiary"];

const spec = ({ document, width: given }) => {
  const light = brand.color.primary.light;
  const accent = document ? light : `var(--fig-accent, ${light})`;
  const paper = document ? brand.color.palette.white : "var(--bs-body-bg, #FAFCFD)";
  // 700px as in prererender
  const w = given ?? (typeof width === "undefined" ? 700 : width);
  return {
    document,
    width: w,
    height: Math.round(w / 2),
    marginLeft: 90,
    marginBottom: 60,
    fx: { label: "birth year", tickFormat: "d" },
    x: { domain: levels, label: "father", tickRotate: -30 },
    y: { domain: levels, reverse: true, label: "mother" },
    opacity: {
      domain: [0, 50],
      range: [0, 1],
      clamp: true,
      legend: true,
      color: accent,
      label: "share of couples (within the year), %",
    },
    marks: [
      Plot.cell(rows, {
        fx: "year",
        x: "father",
        y: "mother",
        fill: accent,
        fillOpacity: (d) => d.share * 100,
        stroke: "currentColor",
        strokeOpacity: 0.12,
      }),
      Plot.text(rows, {
        fx: "year",
        x: "father",
        y: "mother",
        text: "count",
        fontSize: 13,
        fill: (d) => (d.share > 0.35 ? paper : "currentColor"),
      }),
    ],
  };
};
