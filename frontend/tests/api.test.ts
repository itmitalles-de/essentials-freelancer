import { beforeEach, describe, expect, it, vi } from "vitest";

import { api, setToken } from "../src/api";

describe("API client", () => {
  beforeEach(() => {
    vi.unstubAllGlobals();
  });

  it("sends the stored bearer token and JSON body", async () => {
    setToken("synthetic-token");
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ id: 7 }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      })
    );
    vi.stubGlobal("fetch", fetchMock);

    await api.post("/clients", { name: "Example Studio" });

    expect(fetchMock).toHaveBeenCalledWith(
      "/api/clients",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({ name: "Example Studio" }),
        headers: expect.objectContaining({
          Authorization: "Bearer synthetic-token",
          "Content-Type": "application/json",
        }),
      })
    );
  });
});
