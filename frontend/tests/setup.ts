import "@testing-library/jest-dom/vitest";
import { beforeEach } from "vitest";

beforeEach(() => {
  localStorage.clear();
  localStorage.setItem("tracker-lang", "de");
});
