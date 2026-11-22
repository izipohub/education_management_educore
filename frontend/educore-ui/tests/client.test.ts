import { AxiosError, AxiosHeaders } from "axios";
import { describe, expect, it } from "vitest";
import { ApiError, frappeErrorMessage, toApiError } from "@/core/api/client";

function axiosError(status: number, data: unknown) {
  const config = { headers: new AxiosHeaders() };
  return new AxiosError("failed", "ERR", config, null, { status, statusText: "", headers: {}, config, data });
}

describe("frappeErrorMessage", () => {
  it("reads the message Frappe meant for the user, without its HTML", () => {
    const body = {
      _server_messages: JSON.stringify([JSON.stringify({ message: "BSAMS-WHK-FT is <strong>full</strong> for 2027" })]),
    };
    expect(frappeErrorMessage(body, "fallback")).toBe("BSAMS-WHK-FT is full for 2027");
  });

  it("falls back to the exception text, without the exception class", () => {
    expect(frappeErrorMessage({ exception: "frappe.exceptions.ValidationError: Choose an offering" }, "x")).toBe(
      "Choose an offering",
    );
  });

  it("uses the fallback when Frappe sent nothing readable", () => {
    expect(frappeErrorMessage(undefined, "Request failed (500)")).toBe("Request failed (500)");
  });
});

describe("toApiError", () => {
  it("keeps the status and Frappe's exception type", () => {
    const error = toApiError(axiosError(403, { exc_type: "PermissionError", exception: "frappe.exceptions.PermissionError: Not permitted" }));
    expect(error).toBeInstanceOf(ApiError);
    expect(error.status).toBe(403);
    expect(error.type).toBe("PermissionError");
    expect(error.message).toBe("Not permitted");
  });

  it("says when the server could not be reached", () => {
    const config = { headers: new AxiosHeaders() };
    expect(toApiError(new AxiosError("Network Error", "ERR_NETWORK", config)).message).toBe(
      "The server could not be reached",
    );
  });
});
