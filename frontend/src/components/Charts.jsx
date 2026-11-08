function LineChart({ mode = "revenue" }) {
  const line = mode === "sales"
    ? "0,112 45,91 90,100 135,64 180,73 225,52 270,61 315,29 360,41 405,17"
    : "0,105 45,83 90,91 135,57 180,69 225,37 270,48 315,26 360,39 405,12";
  const area = `${line} 405,140 0,140`;

  return (
    <div className="chart-wrap">
      <div className="chart-axis" aria-hidden="true">
        <span>$8k</span><span>$6k</span><span>$4k</span><span>$2k</span><span>$0</span>
      </div>
      <svg
        className="line-chart"
        viewBox="0 0 405 150"
        role="img"
        aria-label={`${mode === "sales" ? "Sales" : "Revenue"} demonstration trend chart, rising over the last six months`}
        preserveAspectRatio="none"
      >
        <defs>
          <linearGradient id={`chart-fill-${mode}`} x1="0" x2="0" y1="0" y2="1">
            <stop offset="0%" stopColor="#2563eb" stopOpacity=".16" />
            <stop offset="100%" stopColor="#2563eb" stopOpacity="0" />
          </linearGradient>
        </defs>
        {[20, 50, 80, 110, 140].map((y) => (
          <line key={y} x1="0" x2="405" y1={y} y2={y} className="chart-gridline" />
        ))}
        <polygon points={area} fill={`url(#chart-fill-${mode})`} />
        <polyline points={line} className="chart-line" />
        {line.split(" ").map((pair) => {
          const [cx, cy] = pair.split(",");
          return <circle key={pair} cx={cx} cy={cy} r="3" className="chart-point" />;
        })}
      </svg>
      <div className="chart-months" aria-hidden="true">
        <span>Jan</span><span>Feb</span><span>Mar</span><span>Apr</span><span>May</span><span>Jun</span>
      </div>
    </div>
  );
}

function DonutChart() {
  return (
    <div className="donut-layout">
      <div className="donut" role="img" aria-label="Demonstration expense breakdown chart">
        <div className="donut__center"><strong>$8,420</strong><span>Total spend</span></div>
      </div>
      <ul className="legend">
        <li><span className="legend__dot legend__dot--blue" />Inventory <b>42%</b></li>
        <li><span className="legend__dot legend__dot--violet" />Operations <b>28%</b></li>
        <li><span className="legend__dot legend__dot--cyan" />Marketing <b>18%</b></li>
        <li><span className="legend__dot legend__dot--gray" />Other <b>12%</b></li>
      </ul>
    </div>
  );
}

export { DonutChart, LineChart };
