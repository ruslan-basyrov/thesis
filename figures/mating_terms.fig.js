const brand = yaml.load(await loadText("_extensions/ruslan-basyrov/acuity/_brand.yml"));

// a schematic, not data: educational distance within the couple against the
// signed difference, mother's education minus father's
const curve = d3.range(-1, 1.001, 0.05).map((x) => ({ x, y: x * x }));

const labels = [
  { x: -0.72, y: 1.08, text: "hypergamy (+)" },
  { x: 0.72, y: 1.08, text: "hypogamy (-)" },
  { x: 0, y: -0.09, text: "homogamy (=)" },
  { x: 0, y: 0.58, text: "disassortative mating" },
  { x: 0, y: 0.42, text: "assortative mating" },
];

const spec = ({ document }) => {
  const accent = document
    ? brand.color.primary.light
    : `var(--fig-accent, ${brand.color.primary.light})`;
  return {
    document,
    width: 320,
    height: 210,
    margin: 6,
    x: { axis: null, domain: [-1.05, 1.05] },
    y: { axis: null, domain: [-0.16, 1.16] },
    marks: [
      Plot.ruleY([0.5], { stroke: "currentColor", strokeOpacity: 0.75, strokeDasharray: "4" }),
      Plot.line(curve, { x: "x", y: "y", stroke: accent, strokeWidth: 2 }),
      Plot.text(labels, { x: "x", y: "y", text: "text" }),
    ],
  };
};
