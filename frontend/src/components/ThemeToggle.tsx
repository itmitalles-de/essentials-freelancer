import { useTheme } from "../contexts/ThemeContext";

export function ThemeToggle() {
  const { choice, setChoice } = useTheme();
  return (
    <select
      value={choice}
      onChange={(e) => setChoice(e.target.value as "system" | "light" | "dark")}
      aria-label="Farbschema"
      title="Farbschema"
    >
      <option value="system">System</option>
      <option value="light">Hell</option>
      <option value="dark">Dunkel</option>
    </select>
  );
}
