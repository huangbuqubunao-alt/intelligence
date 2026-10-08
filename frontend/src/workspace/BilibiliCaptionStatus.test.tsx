import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { BilibiliCaptionStatus } from "./BilibiliImport";
import { UiLanguageProvider } from "./uiLanguage";

describe("Bilibili withdrawn public-caption capability", () => {
  it("explains metadata-only Content and cannot offer a runnable caption retry", () => {
    localStorage.setItem("yia.ui-language", "en");
    render(<UiLanguageProvider><BilibiliCaptionStatus id="BV1xx411c7mD" status="CAPTION_UNAVAILABLE" onCompleted={vi.fn()} /></UiLanguageProvider>);
    expect(screen.getByText("Public Bilibili captions are currently unavailable. This import saves video information only.")).toBeTruthy();
    expect(screen.getByRole("button", { name: "Retry public captions" }).hasAttribute("disabled")).toBe(true);
  });
});
