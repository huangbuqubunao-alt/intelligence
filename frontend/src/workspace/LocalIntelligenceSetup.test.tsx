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
