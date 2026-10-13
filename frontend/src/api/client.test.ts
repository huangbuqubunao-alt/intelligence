import { ApiRequestError, api } from "./client";

test("stable validation code produces actionable product copy and retains diagnostic authority", () => {
  const diagnostic = "Request values are invalid or unavailable.";
  const error = new ApiRequestError({ code: "VALIDATION_ERROR", message: diagnostic, details: { reason_code: "INVALID_INPUT" } });
  expect(error.message).toBe("The request could not be accepted. Check the entered information and try again.");
  expect(error.message).not.toContain(diagnostic);
  expect(error.code).toBe("VALIDATION_ERROR");
  expect(error.details?.reason_code).toBe("INVALID_INPUT");
  expect(error.technicalMessage).toBe(diagnostic);
});

afterEach(() => vi.unstubAllGlobals());

test.each(["GET", "HEAD"])("%s empty 500 is a localized read availability failure, with no automatic retry", async (method) => {
  const fetchMock = vi.fn().mockResolvedValue(new Response("", { status: 500 }));
  vi.stubGlobal("fetch", fetchMock);
  await expect(api("/videos", { method })).rejects.toMatchObject({ code: "READ_SERVICE_UNAVAILABLE" });
  expect(fetchMock).toHaveBeenCalledTimes(1);
});

test("an unreadable successful read is distinct from authorization or task failure", async () => {
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response("<html>temporary response</html>", { status: 200 })));
  await expect(api("/videos")).rejects.toMatchObject({ code: "READ_RESPONSE_INVALID" });
});

test("read error mapping preserves structured qualification and authorization codes", async () => {
  const error = { code: "NO_QUALIFIED_MODEL", message: "Qualification is closed.", details: { reason_code: "QUALIFICATION_FAILED" } };
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(JSON.stringify({ error }), { status: 403 })));
  await expect(api("/videos")).rejects.toMatchObject({ code: error.code, technicalMessage: error.message, details: error.details });
});

test.each(["POST", "PATCH", "PUT", "DELETE"])("%s empty response remains an uncertain mutation failure and is never replayed", async (method) => {
  const fetchMock = vi.fn().mockResolvedValue(new Response("", { status: 500 }));
  vi.stubGlobal("fetch", fetchMock);
  await expect(api("/mutating-command", { method, body: JSON.stringify({ command_id: "synthetic-once" }) })).rejects.toBeInstanceOf(SyntaxError);
  expect(fetchMock).toHaveBeenCalledTimes(1);
});
