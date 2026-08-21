const brand = yaml.load(await loadText("_extensions/ruslan-basyrov/acuity/_brand.yml"));
const rows = JSON.parse(await loadText("build/couples_shares.json"));

// the order as in the shared source data
const levels = ["compulsory", "apprenticeship", "Matura", "tertiary"];
const ALL = "all";
const years = [1990, 2007];

const marginals = (key) =>
  years.flatMap((year) => {
    const within = rows.filter((d) => d.year === year);
    return levels.map((level) => ({
      year,
      mother: key === "mother" ? level : ALL,
      father: key === "father" ? level : ALL,
      share: d3.sum(within.filter((d) => d[key] === level), (d) => d.share),
    }));
  });

const mothers = marginals("mother");
const fathers = marginals("father");

const spec = ({ document, width: given }) => {
  const light = brand.color.primary.light;
  const accent = document ? light : `var(--fig-accent, ${light})`;
  const paper = document ? brand.color.palette.white : "var(--bs-body-bg, #FAFCFD)";
  // 700px as in prerender
  const w = given ?? (typeof width === "undefined" ? 700 : width);
  const percent = (d) => d3.format(".1f")(100 * d.share);
  // margin cells become labelled bars, sized as fractions of the band so html
  // and pdf agree. Both directions use the band height, so equal shares match
  const bars = (data, dir) => (index, scales, values, dimensions, context, next) => {
    const g = next(index, scales, values, dimensions, context);
    [...g.querySelectorAll("rect")].forEach((rect, j) => {
      const share = data[index[j]].share;
      const [x, y, w, h] = ["x", "y", "width", "height"].map((a) => +rect.getAttribute(a));
      const length = share * 0.6 * h;
      const thickness = 0.1 * h;
      if (dir === "x") {
        rect.setAttribute("x", x + w / 8);
        rect.setAttribute("width", length);
        rect.setAttribute("y", y + 0.7 * h);
        rect.setAttribute("height", thickness);
      } else {
        rect.setAttribute("y", y + h / 12);
        rect.setAttribute("height", length);
        rect.setAttribute("x", x + w / 2 - thickness / 2);
        rect.setAttribute("width", thickness);
      }
      const label = context.document.createElementNS("http://www.w3.org/2000/svg", "text");
      label.setAttribute("x", x + w / 2);
      if (dir === "x") {
        // on the row centreline, like the cell values: band centre, 0.32em down
        label.setAttribute("y", y + 0.5 * h);
        label.setAttribute("dy", "0.32em");
      } else {
        label.setAttribute("y", y + 0.75 * h);
      }
      label.setAttribute("text-anchor", "middle");
      label.setAttribute("font-size", 11);
      label.setAttribute("fill", "currentColor");
      label.setAttribute("fill-opacity", 1);
      label.textContent = percent(data[index[j]]);
      g.appendChild(label);
    });
    return g;
  };

  return {
    document,
    width: w,
    height: Math.round(w * 0.56),
    marginLeft: 90,
    marginBottom: 60,
    fx: { domain: years, label: "birth year", tickFormat: "d" },
    x: { domain: [...levels, ALL], label: "father", tickRotate: -30, padding: 0 },
    y: { domain: [ALL, ...levels], reverse: true, label: "mother", padding: 0 },
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
      Plot.cell(mothers, {
        fx: "year",
        x: "father",
        y: "mother",
        fill: "currentColor",
        fillOpacity: 0.3,
        render: bars(mothers, "x"),
      }),
      Plot.cell(fathers, {
        fx: "year",
        x: "father",
        y: "mother",
        fill: "currentColor",
        fillOpacity: 0.3,
        render: bars(fathers, "y"),
      }),
      Plot.text(rows, {
        fx: "year",
        x: "father",
        y: "mother",
        text: percent,
        fontSize: 13,
        fill: (d) => (d.share > 0.35 ? paper : "currentColor"),
      }),
    ],
  };
};
