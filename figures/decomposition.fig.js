const brand = yaml.load(await loadText("_extensions/ruslan-basyrov/acuity/_brand.yml"));
const cells = JSON.parse(await loadText("build/decomposition.json"));

// the order as in the shared source data
const levels = ["compulsory", "apprenticeship", "Matura", "tertiary"];
const hypogamous = (d) => levels.indexOf(d.mother) > levels.indexOf(d.father);
// each row shares association, each column margins, so the observed tables
// are on the main diagonal
const panels = [
  ["1990 margins", "1990 association", "base"],
  ["2007 margins", "1990 association", "counterfactual"],
  ["1990 margins", "2007 association", "reverse"],
  ["2007 margins", "2007 association", "observed"],
];

const inner = panels.flatMap(([margins, association, column]) => {
  const total = d3.sum(cells, (d) => d[column]);
  return cells.map((d) => ({
    margins,
    association,
    mother: d.mother,
    father: d.father,
    hypogamous: hypogamous(d),
    share: d[column] / total,
  }));
});

const rates = panels.map(([margins, association]) => ({
  margins,
  association,
  share: d3.sum(
    inner.filter((d) => d.margins === margins && d.association === association && d.hypogamous),
    (d) => d.share,
  ),
}));

const spec = ({ document, width: given }) => {
  const light = brand.color.primary.light;
  const accent = document ? light : `var(--fig-accent, ${light})`;
  // 700px as in prerender
  const w = given ?? (typeof width === "undefined" ? 700 : width);
  const place = { fx: "margins", fy: "association", x: "father", y: "mother" };
  // wide facet gaps so the arrows between the panels have room
  const pad = 0.15;
  const rate = Object.fromEntries(panels.map(([, , column], i) => [column, rates[i].share]));
  const points = (from, to) => d3.format("+.1f")(100 * (rate[to] - rate[from]));
  // the two paths from 1990 to 2007: above the main diagonal the margins
  // change first, below it the association
  const walks = (dimensions, doc) => {
    const ns = "http://www.w3.org/2000/svg";
    const { width, height, marginLeft, marginTop, marginRight, marginBottom } = dimensions;
    const stepX = (width - marginLeft - marginRight) / (2 - pad);
    const stepY = (height - marginTop - marginBottom) / (2 - pad);
    const bwX = stepX * (1 - pad);
    const bwY = stepY * (1 - pad);
    const out = doc.createElementNS(ns, "g");
    out.setAttribute("stroke", "currentColor");
    out.setAttribute("stroke-opacity", 0.75);
    out.setAttribute("fill", "currentColor");
    const arrow = ([x1, y1], [x2, y2]) => {
      const line = doc.createElementNS(ns, "line");
      const down = x1 === x2;
      line.setAttribute("x1", x1);
      line.setAttribute("y1", y1);
      line.setAttribute("x2", down ? x2 : x2 - 6);
      line.setAttribute("y2", down ? y2 - 6 : y2);
      line.setAttribute("stroke-width", 1.5);
      const head = doc.createElementNS(ns, "path");
      head.setAttribute("d", down
        ? `M${x2},${y2}L${x2 - 3.5},${y2 - 6}L${x2 + 3.5},${y2 - 6}Z`
        : `M${x2},${y2}L${x2 - 6},${y2 - 3.5}L${x2 - 6},${y2 + 3.5}Z`);
      head.setAttribute("stroke", "none");
      head.setAttribute("fill-opacity", 0.75);
      out.append(line, head);
    };
    const label = (text, x, y, anchor) => {
      const node = doc.createElementNS(ns, "text");
      node.setAttribute("x", x);
      node.setAttribute("y", y);
      node.setAttribute("dy", "0.32em");
      node.setAttribute("text-anchor", anchor);
      node.setAttribute("font-size", 12);
      node.setAttribute("stroke", "none");
      node.setAttribute("fill-opacity", 1);
      node.textContent = text;
      out.appendChild(node);
    };
    const gapX = marginLeft + bwX + (stepX - bwX) / 2;
    const gapY = marginTop + bwY + (stepY - bwY) / 2;
    const topY = marginTop + bwY / 2;
    const bottomY = marginTop + stepY + bwY / 2;
    const leftX = marginLeft + bwX / 2;
    const rightX = marginLeft + stepX + bwX / 2;
    arrow([marginLeft + bwX + 3, topY], [marginLeft + stepX - 3, topY]);
    label(points("base", "counterfactual"), gapX, topY - 12, "middle");
    arrow([rightX, marginTop + bwY + 3], [rightX, marginTop + stepY - 3]);
    label(points("counterfactual", "observed"), rightX + 9, gapY, "start");
    arrow([leftX, marginTop + bwY + 3], [leftX, marginTop + stepY - 3]);
    label(points("base", "reverse"), leftX + 9, gapY, "start");
    arrow([marginLeft + bwX + 3, bottomY], [marginLeft + stepX - 3, bottomY]);
    label(points("reverse", "observed"), gapX, bottomY - 12, "middle");
    return out;
  };
  return {
    document,
    width: w,
    height: Math.round(w * 0.8),
    marginTop: 45,
    marginLeft: 110,
    marginRight: 115,
    marginBottom: 60,
    fx: { domain: ["1990 margins", "2007 margins"], label: null, paddingInner: pad, paddingOuter: 0 },
    fy: { domain: ["1990 association", "2007 association"], label: null, paddingInner: pad, paddingOuter: 0 },
    x: { domain: levels, label: "father", tickRotate: -30, padding: 0 },
    y: { domain: levels, reverse: true, label: "mother", padding: 0 },
    opacity: {
      domain: [0, 50],
      range: [0, 1],
      clamp: true,
      legend: true,
      color: accent,
      label: "share of couples (within the panel), %",
    },
    marks: [
      Plot.cell(inner, {
        ...place,
        fill: accent,
        fillOpacity: (d) => d.share * 100,
        stroke: "currentColor",
        strokeOpacity: 0.12,
      }),
      Plot.cell(inner.filter((d) => d.hypogamous), {
        ...place,
        render: (index, scales, values, dimensions, context, next) => {
          const g = next(index, scales, values, dimensions, context);
          const rects = [...g.querySelectorAll("rect")];
          const boxes = rects.map((r) =>
            ["x", "y", "width", "height"].map((a) => +r.getAttribute(a)));
          // the outline of the highlighted area, one step down per row
          const rows = d3.groups(boxes, ([, y]) => y).sort(([a], [b]) => a - b);
          const left = d3.min(boxes, ([x]) => x);
          const corners = [[left, rows[0][0]]];
          for (const [y, row] of rows) {
            const right = d3.max(row, ([x, , w]) => x + w);
            corners.push([right, y], [right, y + row[0][3]]);
          }
          corners.push([left, corners.at(-1)[1]]);
          const path = context.document.createElementNS("http://www.w3.org/2000/svg", "path");
          path.setAttribute("d", `M${corners.map((c) => c.join(",")).join("L")}Z`);
          path.setAttribute("fill", "none");
          path.setAttribute("stroke", "currentColor");
          path.setAttribute("stroke-opacity", 0.75);
          path.setAttribute("stroke-width", 1.5);
          rects.forEach((r) => r.remove());
          g.appendChild(path);
          return g;
        },
      }),
      Plot.text(rates, {
        fx: "margins",
        fy: "association",
        frameAnchor: "top-left",
        dx: 7,
        dy: 9,
        text: (d) => d3.format(".1f")(100 * d.share) + "%",
        fontSize: 16,
        fontWeight: "bold",
      }),
      Plot.frame({
        facet: "super",
        stroke: "none",
        render: (index, scales, values, dimensions, context, next) => {
          // next returns the frame's rect, which cannot hold children
          const g = context.document.createElementNS("http://www.w3.org/2000/svg", "g");
          g.append(next(index, scales, values, dimensions, context), walks(dimensions, context.document));
          return g;
        },
      }),
    ],
  };
};
