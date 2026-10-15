// Área segura: 12% de margem no topo e 22% embaixo. A legenda fica dentro dela.
// Usa um div comum: AbsoluteFill define width 100%, o que estoura a margem lateral.
export const SafeArea: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <div
    style={{
      position: "absolute",
      top: "12%",
      bottom: "22%",
      left: 80,
      right: 80,
      display: "flex",
      flexDirection: "column",
      justifyContent: "center",
    }}
  >
    {children}
  </div>
);
