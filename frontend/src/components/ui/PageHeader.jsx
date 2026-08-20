export default function PageHeader({ title, description, actions }) {
  return (
    <div
      style={{
        display: "flex",
        alignItems: "flex-start",
        justifyContent: "space-between",
        gap: "1rem",
        flexWrap: "wrap",
        marginBottom: "1.25rem",
      }}
    >
      <div>
        <h1 style={{ margin: 0, fontSize: "1.4rem", fontWeight: 700 }}>{title}</h1>
        {description && (
          <p className="muted" style={{ margin: "0.3rem 0 0", fontSize: "0.9rem" }}>
            {description}
          </p>
        )}
      </div>
      {actions && <div style={{ display: "flex", gap: "0.5rem", alignItems: "center", flexWrap: "wrap" }}>{actions}</div>}
    </div>
  );
}
