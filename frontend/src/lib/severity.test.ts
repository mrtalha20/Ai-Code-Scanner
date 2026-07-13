import { severityLabel, severityColor, severityRingColor } from "@/lib/severity";

describe("severityLabel", () => {
  it("returns Critical for 9-10", () => {
    expect(severityLabel(9)).toBe("Critical");
    expect(severityLabel(10)).toBe("Critical");
  });
  it("returns High for 7-8", () => {
    expect(severityLabel(7)).toBe("High");
    expect(severityLabel(8)).toBe("High");
  });
  it("returns Medium for 4-6", () => {
    expect(severityLabel(4)).toBe("Medium");
    expect(severityLabel(6)).toBe("Medium");
  });
  it("returns Low for 1-3", () => {
    expect(severityLabel(1)).toBe("Low");
    expect(severityLabel(3)).toBe("Low");
  });
});

describe("severityColor", () => {
  it("returns red class for critical", () => {
    expect(severityColor(10)).toContain("red");
  });
  it("returns green class for low", () => {
    expect(severityColor(2)).toContain("green");
  });
});

describe("severityRingColor", () => {
  it("returns hex color string", () => {
    const color = severityRingColor(9);
    expect(color).toMatch(/^#[0-9a-f]{6}$/i);
  });
});
