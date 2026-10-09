import { ApiRequestError } from "./client";

test("stable validation code produces actionable product copy and retains diagnostic authority", () => {
  const diagnostic = "Request values are invalid or unavailable.";
  const error = new ApiRequestError({ code: "VALIDATION_ERROR", message: diagnostic, details: { reason_code: "INVALID_INPUT" } });
  expect(error.message).toBe("The request could not be accepted. Check the entered information and try again.");
  expect(error.message).not.toContain(diagnostic);
  expect(error.code).toBe("VALIDATION_ERROR");
  expect(error.details?.reason_code).toBe("INVALID_INPUT");
  expect(error.technicalMessage).toBe(diagnostic);
});
