import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { LocalIntelligenceSetup } from "./LocalIntelligenceSetup";
import { UiLanguageProvider } from "./uiLanguage";
const model = "qwen3.5:9b-q4_K_M";
const candidate = { candidate_id: "fixed-0406", model, runtime: "0.40.6", catalog_hash: "a".repeat(64), installation: "READY" };
const initial = () => ({ status: "NOT_CONFIGURED", etag: "b".repeat(64), selected_candidate_id: null as string | null,
  actual_route: { provider: "ollama", model: "qwen3:8b", profile_id: null }, candidates: [candidate], blocking_work: [] });
const response = (data: unknown, ok = true) => ({ ok, json: async () => data });
function view(fetcher: ReturnType<typeof vi.fn>) {
  localStorage.setItem("yia.ui-language", "en"); vi.stubGlobal("fetch", fetcher);
  render(<UiLanguageProvider><LocalIntelligenceSetup pollMillis={1} /></UiLanguageProvider>);
}
afterEach(() => { cleanup(); vi.unstubAllGlobals(); localStorage.clear(); });
it("requires explicit selection and confirms actual route after restart", async () => {
  let state = initial(); let writes = 0;
  const fetcher = vi.fn(async (_path: string, options?: RequestInit) => {
    if (options?.method === "PUT") {
      writes++;
      expect(JSON.parse(options.body as string)).toEqual({ candidate_id: candidate.candidate_id, expected_etag: initial().etag });
      state = { ...state, status: "APPLIED", selected_candidate_id: candidate.candidate_id, actual_route: { provider: "ollama", model, profile_id: null } };
      return response({ local_intelligence: { ...state, status: "APPLYING", actual_route: initial().actual_route } });
    }
    return response({ local_intelligence: state });
  });
  view(fetcher); const radio = await screen.findByRole("radio");
  const button = screen.getByRole("button", { name: "Save and apply Intelligence model" }) as HTMLButtonElement;
  expect(button.disabled).toBe(true); fireEvent.click(radio); fireEvent.click(button);
  await screen.findByText("The Intelligence model selection is applied. Quality verification and execution eligibility are unchanged.");
  expect(writes).toBe(1); expect(document.body.textContent).toContain("Actual Intelligence route: " + model);
  expect(document.body.textContent).toContain("does not download, load, run or qualify");
});
it.each(["CONFIGURATION_BUSY", "CONFIGURATION_CONFLICT", "MODEL_NOT_READY"])("keeps draft and unfinished Content link on %s", async code => {
  const state = { ...initial(), blocking_work: [{ video_id: "local:old", status: "WAITING_MODEL" }] };
  const fetcher = vi.fn(async (_path: string, options?: RequestInit) => options?.method === "PUT"
    ? response({ error: { code, message: "/private/raw" } }, false) : response({ local_intelligence: state }));
  view(fetcher); fireEvent.click(await screen.findByRole("radio"));
  fireEvent.click(screen.getByRole("button", { name: "Save and apply Intelligence model" })); await screen.findByRole("alert");
  expect((screen.getByRole("radio") as HTMLInputElement).checked).toBe(true); expect(document.body.textContent).not.toContain("/private/raw");
  expect(screen.getByRole("link", { name: "Open affected Content" }).getAttribute("href")).toBe("#Content/local%3Aold");
  expect(fetcher.mock.calls.filter(([, init]) => init?.method === "PUT")).toHaveLength(1);
});
it("never retries uncertain save and confirms with GET", async () => {
  let written = false;
  const fetcher = vi.fn(async (_path: string, options?: RequestInit) => {
    if (options?.method === "PUT") { written = true; throw Error("connection closed"); }
    return response({ local_intelligence: written ? { ...initial(), status: "APPLIED", selected_candidate_id: candidate.candidate_id,
      actual_route: { provider: "ollama", model, profile_id: null } } : initial() });
  });
  view(fetcher); fireEvent.click(await screen.findByRole("radio"));
  fireEvent.click(screen.getByRole("button", { name: "Save and apply Intelligence model" }));
  await screen.findByText("The Intelligence model selection is applied. Quality verification and execution eligibility are unchanged.");
  expect(fetcher.mock.calls.filter(([, init]) => init?.method === "PUT")).toHaveLength(1);
});
it.each(["NOT_INSTALLED", "IDENTITY_MISMATCH", "RUNTIME_MISMATCH", "UNAVAILABLE"])("closes incompatible installation (%s)", async installation => {
  view(vi.fn(async () => response({ local_intelligence: { ...initial(), candidates: [{ ...candidate, installation }] } })));
  expect((await screen.findByRole("radio") as HTMLInputElement).disabled).toBe(true);
  expect((screen.getByRole("button", { name: "Save and apply Intelligence model" }) as HTMLButtonElement).disabled).toBe(true);
});
it("rejects malformed applied status then refreshes without writing", async () => {
  const fetcher = vi.fn().mockResolvedValueOnce(response({ local_intelligence: { ...initial(), status: "APPLIED" } }))
    .mockResolvedValue(response({ local_intelligence: { ...initial(), status: "INVALID" } }));
  view(fetcher); await screen.findByRole("alert"); fireEvent.click(screen.getByRole("button", { name: "Refresh model settings" }));
  await screen.findByText("Saved local model settings are invalid. Select the fixed model to repair them safely.");
  expect(fetcher.mock.calls.every(([, init]) => !init?.method)).toBe(true);
});

// Actual isolated /api/v1/settings/local-intelligence response, 2026-10-25.
// SHA256 of the unchanged complete response: 08eb46880bd0c72daa09bd808cf5d5e8149007d6cd5d970f2e97b95b59b0888b.
// Installation is UNAVAILABLE and settings grant no model qualification.
const realThreeCatalogSetup = {
  "status": "NOT_CONFIGURED",
  "etag": "11166c17229ddab7eec68caa81bb9d87b65d89a4c6089cf0f6987b3538ee8c74",
  "selected_candidate_id": null,
  "actual_route": {
    "provider": "ollama",
    "model": "qwen3:8b",
    "profile_id": null
  },
  "restart_required": false,
  "blocking_work": [],
  "error_code": null,
  "candidates": [
    {
      "candidate_id": "local-grounding-qwen35-9b-fixed-runtime-v2",
      "model": "qwen3.5:9b-q4_K_M",
      "model_digest": "sha256:56671c2ab9385f9cfcb404638e32cd62d88e3501d44822208363c010179a3c90",
      "runtime": "0.40.1",
      "catalog_hash": "92b37a8d2c2dbfe8e41946fb88e11fda55f9517f2fe023e9eea76395d968559a",
      "installation": "UNAVAILABLE",
      "qualification": "NOT_GRANTED_BY_SETTINGS"
    },
    {
      "candidate_id": "local-intelligence-qwen35-9b-ollama-0.40.6-v1",
      "model": "qwen3.5:9b-q4_K_M",
      "model_digest": "sha256:56671c2ab9385f9cfcb404638e32cd62d88e3501d44822208363c010179a3c90",
      "runtime": "0.40.6",
      "catalog_hash": "06ceaa109cc4cb05f40612c3e41235789191188ec7220be22421a7d924048da3",
      "installation": "UNAVAILABLE",
      "qualification": "NOT_GRANTED_BY_SETTINGS"
    },
    {
      "candidate_id": "local-intelligence-qwen35-9b-ollama-0.40.9-v2",
      "model": "qwen3.5:9b-q4_K_M",
      "model_digest": "sha256:56671c2ab9385f9cfcb404638e32cd62d88e3501d44822208363c010179a3c90",
      "runtime": "0.40.9",
      "catalog_hash": "14a5f3f6888314d9dd1bb35ae4fd0327a3cff641214db24f4b0f446ce7a08525",
      "installation": "UNAVAILABLE",
      "qualification": "NOT_GRANTED_BY_SETTINGS"
    }
  ]
};

it("renders all three real finite catalogs and explains the unavailable service", async () => {
  const fetcher = vi.fn(async (_path: string, _options?: RequestInit) => response({ local_intelligence: realThreeCatalogSetup }));
  view(fetcher);
  const radios = await screen.findAllByRole("radio");
  expect(radios).toHaveLength(3);
  for (const runtime of ["0.40.1", "0.40.6", "0.40.9"]) {
    expect(screen.getByRole("radio", { name: `${model} · Ollama ${runtime}` })).toBeTruthy();
  }
  expect(radios.every(radio => (radio as HTMLInputElement).disabled)).toBe(true);
  expect(screen.getAllByText("The local model service is unavailable. Start it locally, then read the status again.")).toHaveLength(3);
  expect(screen.queryByRole("alert")).toBeNull();
  expect((screen.getByRole("button", { name: "Save and apply Intelligence model" }) as HTMLButtonElement).disabled).toBe(true);
  expect(fetcher.mock.calls.every(([, init]) => !init?.method)).toBe(true);
});
it("retains compatibility with the prior two-catalog response", async () => {
  view(vi.fn(async () => response({ local_intelligence: {
    ...realThreeCatalogSetup, candidates: realThreeCatalogSetup.candidates.slice(0, 2),
  } })));
  expect(await screen.findAllByRole("radio")).toHaveLength(2);
  expect(screen.queryByRole("alert")).toBeNull();
});
it("only permits the READY choice among three catalogs without treating it as qualification", async () => {
  const candidates = realThreeCatalogSetup.candidates.map((entry, index) => ({
    ...entry, installation: index === 1 ? "READY" : "RUNTIME_MISMATCH",
  }));
  view(vi.fn(async () => response({ local_intelligence: { ...realThreeCatalogSetup, candidates } })));
  const radios = await screen.findAllByRole("radio") as HTMLInputElement[];
  expect(radios.map(radio => radio.disabled)).toEqual([true, false, true]);
  const button = screen.getByRole("button", { name: "Save and apply Intelligence model" }) as HTMLButtonElement;
  expect(button.disabled).toBe(true);
  fireEvent.click(radios[1]);
  expect(button.disabled).toBe(false);
  expect(screen.getAllByText("The installed Ollama version does not match the required version shown above. This selection cannot apply.")).toHaveLength(2);
  expect(screen.getByText("Saving checks installed identity only. It does not download, load, run or qualify a model.")).toBeTruthy();
});
it.each([
  ["empty", []],
  ["four unique catalogs", [...realThreeCatalogSetup.candidates, { ...candidate, candidate_id: "unsupported-fourth" }]],
  ["duplicate catalog identity", [...realThreeCatalogSetup.candidates.slice(0, 2), realThreeCatalogSetup.candidates[1]]],
  ["malformed third catalog", [...realThreeCatalogSetup.candidates.slice(0, 2), null]],
  ["unknown installation", [...realThreeCatalogSetup.candidates.slice(0, 2), { ...realThreeCatalogSetup.candidates[2], installation: "QUALIFIED" }]],
  ["missing runtime", [...realThreeCatalogSetup.candidates.slice(0, 2), { ...realThreeCatalogSetup.candidates[2], runtime: "" }]],
])("rejects %s without offering selection or writing", async (_label, candidates) => {
  const fetcher = vi.fn(async (_path: string, _options?: RequestInit) => response({ local_intelligence: { ...realThreeCatalogSetup, candidates } }));
  view(fetcher);
  await screen.findByRole("alert");
  expect(screen.queryByRole("radio")).toBeNull();
  expect(screen.queryByRole("button", { name: "Save and apply Intelligence model" })).toBeNull();
  expect(fetcher.mock.calls.every(([, init]) => !init?.method)).toBe(true);
});
