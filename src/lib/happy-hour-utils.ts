import { HappyHourPlace, ParsedHappyHour } from "@/types/happy-hour";

const DAYS = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"];

export function parseHappyHourTimes(happyHourString: string): ParsedHappyHour[] {
  if (!happyHourString || happyHourString.trim() === "") {
    return [];
  }

  const result: ParsedHappyHour[] = [];
  const dayEntries = happyHourString.split(" | ");

  for (const entry of dayEntries) {
    const [day, timeRange] = entry.split(": ");
    if (!day || !timeRange) continue;

    const dayName = day.trim();

    if (timeRange.toLowerCase() === "closed") {
      result.push({
        day: dayName,
        startTime: "",
        endTime: "",
      });
      continue;
    }

    // Handle multiple sessions (e.g., "3:00 – 6:00 PM, 10:00 – 11:00 PM")
    const sessions = timeRange.split(", ");

    if (sessions.length === 1) {
      const times = parseTimeRange(sessions[0]);
      if (times) {
        result.push({
          day: dayName,
          startTime: times.start,
          endTime: times.end,
        });
      }
    } else if (sessions.length >= 2) {
      const times1 = parseTimeRange(sessions[0]);
      const times2 = parseTimeRange(sessions[1]);
      if (times1) {
        result.push({
          day: dayName,
          startTime: times1.start,
          endTime: times1.end,
          isSecondSession: true,
          startTime2: times2?.start || "",
          endTime2: times2?.end || "",
        });
      }
    }
  }

  return result;
}

function parseTimeRange(timeStr: string): { start: string; end: string } | null {
  // Handle en-dash and regular dash
  const normalized = timeStr.replace(/–/g, "-").trim();
  const parts = normalized.split(" - ");

  if (parts.length !== 2) return null;

  return {
    start: parts[0].trim(),
    end: parts[1].trim(),
  };
}

export function isInHappyHour(
  place: HappyHourPlace,
  dayIndex: number,
  hour: number,
  minute: number
): boolean {
  const happyHours = parseHappyHourTimes(place.happy_hour_times);
  const dayName = DAYS[dayIndex];

  const dayHappyHour = happyHours.find((hh) => hh.day === dayName);
  if (!dayHappyHour || !dayHappyHour.startTime) return false;

  const currentMinutes = hour * 60 + minute;

  // Check first session
  if (isTimeInRange(currentMinutes, dayHappyHour.startTime, dayHappyHour.endTime)) {
    return true;
  }

  // Check second session if exists
  if (dayHappyHour.isSecondSession && dayHappyHour.startTime2) {
    if (isTimeInRange(currentMinutes, dayHappyHour.startTime2, dayHappyHour.endTime2 || "")) {
      return true;
    }
  }

  return false;
}

function isTimeInRange(currentMinutes: number, startTime: string, endTime: string): boolean {
  const start = timeToMinutes(startTime);
  const end = timeToMinutes(endTime);

  if (start === null || end === null) return false;

  // Handle cases where happy hour spans midnight
  if (end < start) {
    return currentMinutes >= start || currentMinutes <= end;
  }

  return currentMinutes >= start && currentMinutes <= end;
}

function timeToMinutes(timeStr: string): number | null {
  if (!timeStr) return null;

  // Remove narrow non-breaking spaces and normalize
  const normalized = timeStr.replace(/\u202f/g, " ").trim();

  // Match time like "3:00 PM" or "12:00 AM"
  const match = normalized.match(/(\d+):(\d+)\s*(AM|PM)/i);
  if (!match) return null;

  let hours = parseInt(match[1], 10);
  const minutes = parseInt(match[2], 10);
  const period = match[3].toUpperCase();

  if (period === "PM" && hours !== 12) {
    hours += 12;
  } else if (period === "AM" && hours === 12) {
    hours = 0;
  }

  return hours * 60 + minutes;
}

export function hasHappyHour(place: HappyHourPlace): boolean {
  return !!(place.happy_hour_times && place.happy_hour_times.trim() !== "");
}

export function formatHappyHours(place: HappyHourPlace): string {
  if (!hasHappyHour(place)) return "No happy hour info";

  const parsed = parseHappyHourTimes(place.happy_hour_times);
  if (parsed.length === 0) return place.happy_hour_times;

  return parsed
    .map((hh) => {
      if (!hh.startTime) return `${hh.day}: Closed`;
      let result = `${hh.day}: ${hh.startTime} - ${hh.endTime}`;
      if (hh.isSecondSession && hh.startTime2) {
        result += `, ${hh.startTime2} - ${hh.endTime2}`;
      }
      return result;
    })
    .join(" | ");
}

export function getDayHappyHour(place: HappyHourPlace, dayIndex: number): string {
  if (!hasHappyHour(place)) return "";

  const parsed = parseHappyHourTimes(place.happy_hour_times);
  const dayName = DAYS[dayIndex];
  const dayHH = parsed.find((hh) => hh.day === dayName);

  if (!dayHH || !dayHH.startTime) return "";

  let result = `${dayHH.startTime} - ${dayHH.endTime}`;
  if (dayHH.isSecondSession && dayHH.startTime2) {
    result += `, ${dayHH.startTime2} - ${dayHH.endTime2}`;
  }
  return result;
}

export function formatPriceLevel(priceLevel: string): string {
  if (!priceLevel) return "";

  const map: Record<string, string> = {
    PRICE_LEVEL_INEXPENSIVE: "$",
    PRICE_LEVEL_MODERATE: "$$",
    PRICE_LEVEL_EXPENSIVE: "$$$",
    PRICE_LEVEL_VERY_EXPENSIVE: "$$$$",
  };

  return map[priceLevel] || "";
}

export function formatPhone(phone: string): string {
  if (!phone) return "";
  return phone.replace(/^\+1\s*/, "");
}
