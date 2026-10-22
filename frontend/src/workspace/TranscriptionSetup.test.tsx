import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, expect, it, vi } from "vitest";
import { TranscriptionSetup, transcriptionGuidance } from "./TranscriptionSetup";
import { UiLanguageProvider } from "./uiLanguage";
const available = { state: "READY", runtime_detected: true, runtime_available: true, model_present: true, executor_compatible: true, executor: "fixture", qualification_state: "PASSED", production_eligible: true };
afterEach(() => { cleanup(); vi.unstubAllGlobals(); location.hash = ""; });
function view(capability = available, fail?: string) {
  localStorage.setItem("yia.ui-language", "en");
  const fetch = vi.fn(async (_path: string, options?: RequestInit) => {
    if (fail && options?.method === "PUT") return { ok: false, json: async () => ({ error: { code: fail, message: "/private/raw failure" } }) };
    return { ok: true, json: async () => ({ capability }) };
  });
  vi.stubGlobal("fetch", fetch);
  render(<UiLanguageProvider><TranscriptionSetup /></UiLanguageProvider>);
  return fetch;
}
it.each([
  [{ ...available, runtime_available: false }, "speech runtime is unavailable"],
  [{ ...available, model_present: false }, "No local speech model is selected"],
  [{ ...available, executor_compatible: false }, "incompatible with the local runtime"],
  [{ ...available, reason_code: "MODEL_INVALID" }, "not a compatible local speech model"],
  [{ ...available, reason_code: "MEDIA_TOOL_UNAVAILABLE" }, "media tools"],
  [{ ...available, qualification_state: "FAILED", production_eligible: false }, "failed speech quality"],
  [{ ...available, qualification_state: "STALE", production_eligible: false }, "changed since verification"],
  [{ ...available, qualification_state: "NOT_TESTED", production_eligible: false }, "has not passed quality"],
  [{ ...available, qualification_state: "RUNNING", production_eligible: false }, "verification is in progress"],
  [{ ...available, checking: true }, "Checking local transcription"],
])("explains readiness without claiming usable transcription: %j", (capability, phrase) => {
  expect(transcriptionGuidance(capability)).toContain(phrase);
  expect(transcriptionGuidance(capability)).not.toContain("is ready.");
});
it("requires production eligibility even when assets report READY", () => {
  expect(transcriptionGuidance({ ...available, production_eligible: false })).toContain("does not qualify");
});
it("saves only the explicit local path, without model execution or qualification", async () => {
  const fetch = view({ ...available, model_present: false, production_eligible: false });
  await screen.findByText(/No local speech model is selected/);
  await userEvent.type(screen.getByLabelText("Local speech model directory"), "  /installed/speech-model  ");
  await userEvent.click(screen.getByRole("button", { name: "Save and check model" }));
  await screen.findByText("Model selection saved.");
  const writes = fetch.mock.calls.filter(([, options]) => options?.method);
  expect(writes).toHaveLength(1);
  expect(writes[0][0]).toBe("/api/v1/local/transcription/model");
  expect(writes[0][1]?.body).toBe(JSON.stringify({ model_path: "/installed/speech-model" }));
  expect((screen.getByLabelText("Local speech model directory") as HTMLInputElement).value).toBe("");
  expect(screen.queryByRole("button", { name: "Start transcription" })).toBeNull();
  expect(document.body.textContent).toContain("No local speech model is selected");
});
it.each(["MODEL_INVALID", "TRANSCRIPTION_BUSY", "OTHER_FAILURE"])("keeps the model draft and localizes errors (%s)", async code => {
  view(available, code);
  await screen.findByText(/Local transcription is ready/);
  await userEvent.type(screen.getByLabelText("Local speech model directory"), "/chosen/model");
  await userEvent.click(screen.getByRole("button", { name: "Save and check model" }));
  expect((await screen.findByRole("alert")).textContent).toMatch(/absolute path|running|local connection/);
  expect(document.body.textContent).not.toContain("/private/raw");
  expect((screen.getByLabelText("Local speech model directory") as HTMLInputElement).value).toBe("/chosen/model");
});
it("retries a connection failure and returns to the exact Content", async () => {
  location.hash = "#Settings/transcription/local%3Acontent";
  const fetch = vi.fn().mockRejectedValueOnce(new Error("Network lost")).mockResolvedValue({ ok: true, json: async () => ({ capability: available }) });
  vi.stubGlobal("fetch", fetch);
  localStorage.setItem("yia.ui-language", "en");
  render(<UiLanguageProvider><TranscriptionSetup /></UiLanguageProvider>);
  await screen.findByText("Transcription status could not be checked. Check the local connection and try again.");
  await userEvent.click(screen.getByRole("button", { name: "Retry status check" }));
  await screen.findByText(/Local transcription is ready/);
  expect(screen.getByRole("link", { name: "Back to Content" }).getAttribute("href")).toBe("#Content/local%3Acontent");
  expect(fetch.mock.calls[1][0]).toBe("/api/v1/local/transcription/capability");
  expect(fetch.mock.calls.every(([, options]) => !options?.method)).toBe(true);
});
it("prevents model changes during a live check", async () => {
  view({ ...available, qualification_state: "RUNNING", production_eligible: false });
  await screen.findByText(/Speech quality verification is in progress/);
  expect(screen.getByRole("button", { name: "Save and check model" }).hasAttribute("disabled")).toBe(true);
  expect(screen.getByLabelText("Local speech model directory").hasAttribute("disabled")).toBe(true);
});

it("can retry status after a live check loses connection without changing its model", async () => {
  localStorage.setItem("yia.ui-language", "en");
  const fetch = vi.fn()
    .mockResolvedValueOnce({ ok: true, json: async () => ({ capability: { ...available, checking: true, production_eligible: false } }) })
    .mockRejectedValueOnce(new TypeError("Failed to fetch"))
    .mockResolvedValue({ ok: true, json: async () => ({ capability: available }) });
  vi.stubGlobal("fetch", fetch);
  render(<UiLanguageProvider><TranscriptionSetup /></UiLanguageProvider>);
  await screen.findByText("Transcription status could not be checked. Check the local connection and try again.", {}, { timeout: 3000 });
  expect(screen.getByLabelText("Local speech model directory").hasAttribute("disabled")).toBe(true);
  const retry = screen.getByRole("button", { name: "Retry status check" });
  expect(retry.hasAttribute("disabled")).toBe(false);
  await userEvent.click(retry);
  await screen.findByText(/Local transcription is ready/);
  expect(fetch.mock.calls.every(([, options]) => !options?.method)).toBe(true);
});
