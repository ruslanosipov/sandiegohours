import { HappyHourPlace, ParsedHappyHour } from "@/types/happy-hour";

const DAYS = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"];

export enum HappyHourStatus {
  NO_HAPPY_HOUR = 'NO_HAPPY_HOUR',
  NO_HAPPY_HOUR_TODAY = 'NO_HAPPY_HOUR_TODAY',
  ACTIVE = 'ACTIVE',
  LATER_TODAY = 'LATER_TODAY',
  PASSED_TODAY = 'PASSED_TODAY',
}

export function parseHappyHourTimes(happyHourString: string): ParsedHappyHour[] {
  if (!happyHourString || happyHourString.trim() === "") {
    return [];
  }

  // Preprocess to fix missing spaces between days
  const processedString = preprocessHappyHourString(happyHourString);

  const result: ParsedHappyHour[] = [];
  const dayEntries = processedString.split(" | ");

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

/**
 * Parse a time string like "3:00 PM" to minutes from midnight
 */
export function parseTimeToMinutes(timeStr: string): number {
  const normalized = timeStr.replace(/\u202f/g, " ").trim();
  
  // Try "HH:MM AM/PM" format
  let match = normalized.match(/(\d+):(\d+)\s*(AM|PM)/i);
  if (match) {
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
  
  return 0;
}

/**
 * Check if happy hour is currently active for a given time string and current date
 */
export function isHappyHourActive(happyHourTimes: string, now: Date = new Date()): boolean {
  if (!happyHourTimes || happyHourTimes.trim() === "") {
    return false;
  }

  // Preprocess to fix missing spaces between days
  const processedTimes = preprocessHappyHourString(happyHourTimes);
  
  const currentDayIndex = now.getDay();
  const currentMinutes = now.getHours() * 60 + now.getMinutes();
  
  // Parse each day entry (format: "Monday: 3:00 PM - 6:00 PM | Tuesday: ...")
  const dayEntries = processedTimes.split(" | ");
  
  for (const entry of dayEntries) {
    const dayMatch = entry.match(/^([^:]+):\s*(.+)$/i);
    if (!dayMatch) continue;
    
    const dayName = dayMatch[1].trim();
    const timeRange = dayMatch[2].trim();
    
    // Case insensitive day matching
    const entryDayIndex = DAYS.findIndex(d => d.toLowerCase() === dayName.toLowerCase());
    if (entryDayIndex !== currentDayIndex) continue;
    
    // Skip if marked as closed
    if (timeRange.toLowerCase() === "closed") continue;
    
    // Parse time ranges (handle multiple sessions: "3:00 PM - 6:00 PM, 10:00 PM - 12:00 AM")
    // Also handle en-dash (–) and other dash variants
    const normalizedRange = timeRange.replace(/[\u2013\u2014]/g, '-');
    const sessions = normalizedRange.split(", ");
    
    for (const session of sessions) {
      const times = session.split(" - ");
      if (times.length !== 2) continue;
      
      const startTimeRaw = times[0].trim();
      const endTimeRaw = times[1].trim();
      
      // If start time doesn't have AM/PM but end time does, inherit it
      const startHasAmPm = /(am|pm|AM|PM)/i.test(startTimeRaw);
      const endHasAmPm = /(am|pm|AM|PM)/i.test(endTimeRaw);
      
      let startTime = startTimeRaw;
      if (!startHasAmPm && endHasAmPm) {
        // Extract AM/PM from end time and append to start time
        const endAmPm = endTimeRaw.match(/(am|pm|AM|PM)/i)?.[0] || '';
        startTime = `${startTimeRaw} ${endAmPm}`;
      }
      
      const startMinutes = parseFlexibleTime(startTime);
      const endMinutes = parseFlexibleTime(endTimeRaw);
      
      // Handle midnight span
      if (endMinutes < startMinutes) {
        if (currentMinutes >= startMinutes || currentMinutes <= endMinutes) {
          return true;
        }
      } else {
        if (currentMinutes >= startMinutes && currentMinutes <= endMinutes) {
          return true;
        }
      }
    }
  }
  
  return false;
}

/**
 * Get the status of happy hour for display
 */
export function getHappyHourStatus(happyHourTimes: string, now: Date = new Date()): HappyHourStatus {
  if (!happyHourTimes || happyHourTimes.trim() === "") {
    return HappyHourStatus.NO_HAPPY_HOUR;
  }

  // Preprocess to fix missing spaces between days
  const processedTimes = preprocessHappyHourString(happyHourTimes);

  // Check if active now
  if (isHappyHourActive(happyHourTimes, now)) {
    return HappyHourStatus.ACTIVE;
  }

  const currentDayIndex = now.getDay();
  const currentMinutes = now.getHours() * 60 + now.getMinutes();
  
  // Check today's status (use processed times)
  const dayEntries = processedTimes.split(" | ");
  
  let todayStatus: 'closed' | 'later' | 'passed' | 'none' = 'none';
  
  for (const entry of dayEntries) {
    const dayMatch = entry.match(/^([^:]+):\s*(.+)$/i);
    if (!dayMatch) continue;
    
    const dayName = dayMatch[1].trim();
    const timeRange = dayMatch[2].trim();
    
    // Case insensitive day matching
    const entryDayIndex = DAYS.findIndex(d => d.toLowerCase() === dayName.toLowerCase());
    
    if (entryDayIndex === currentDayIndex) {
      if (timeRange.toLowerCase() === "closed") {
        todayStatus = 'closed';
      } else {
        // Parse times with AM/PM inheritance
        // Normalize dashes first
        const normalizedRange = timeRange.replace(/[\u2013\u2014]/g, '-');
        const sessions = normalizedRange.split(", ");
        const times = sessions[0].split(" - ");
        if (times.length === 2) {
          let startTime = times[0].trim();
          const endTimeRaw = times[1].trim();
          
          // Inherit AM/PM if needed
          const startHasAmPm = /(am|pm|AM|PM)/i.test(startTime);
          const endHasAmPm = /(am|pm|AM|PM)/i.test(endTimeRaw);
          if (!startHasAmPm && endHasAmPm) {
            const endAmPm = endTimeRaw.match(/(am|pm|AM|PM)/i)?.[0] || '';
            startTime = `${startTime} ${endAmPm}`;
          }
          
          const startMinutes = parseFlexibleTime(startTime);
          const endMinutes = parseFlexibleTime(endTimeRaw);
          
          if (currentMinutes < startMinutes) {
            todayStatus = 'later';
          } else if (currentMinutes > endMinutes) {
            todayStatus = 'passed';
          }
        }
      }
      break;
    }
  }
  
  // Map status to enum
  if (todayStatus === 'closed') {
    // Has happy hour info but closed today
    return HappyHourStatus.NO_HAPPY_HOUR_TODAY;
  }
  
  if (todayStatus === 'none') {
    // Check if there are any happy hours at all
    const hasAnyHappyHour = dayEntries.some(entry => {
      const match = entry.match(/^([^:]+):\s*(.+)$/i);
      if (!match) return false;
      const timeRange = match[2].trim();
      return timeRange.toLowerCase() !== 'closed' && timeRange !== '';
    });
    
    if (hasAnyHappyHour) {
      return HappyHourStatus.NO_HAPPY_HOUR_TODAY;
    }
    return HappyHourStatus.NO_HAPPY_HOUR;
  }
  
  if (todayStatus === 'later') {
    return HappyHourStatus.LATER_TODAY;
  }
  
  if (todayStatus === 'passed') {
    return HappyHourStatus.PASSED_TODAY;
  }
  
  return HappyHourStatus.NO_HAPPY_HOUR;
}

/**
 * Get a display label for the happy hour status
 */
export function getHappyHourStatusLabel(status: HappyHourStatus): { text: string; colorClass: string } {
  switch (status) {
    case HappyHourStatus.ACTIVE:
      return { text: "Happy Hour Now!", colorClass: "bg-green-100 text-green-700" };
    case HappyHourStatus.NO_HAPPY_HOUR:
      return { text: "No Happy Hour", colorClass: "bg-red-100 text-red-700" };
    case HappyHourStatus.NO_HAPPY_HOUR_TODAY:
      return { text: "No Happy Hour Today", colorClass: "bg-gray-100 text-gray-700" };
    case HappyHourStatus.LATER_TODAY:
      return { text: "Happy Hour Later", colorClass: "bg-blue-100 text-blue-700" };
    case HappyHourStatus.PASSED_TODAY:
      return { text: "Happy Hour Passed", colorClass: "bg-gray-100 text-gray-700" };
    default:
      return { text: "", colorClass: "" };
  }
}

/**
 * Normalize time format to "HH:MM AM/PM" standard
 * Handles various inconsistent formats like "3pm", "3:00pm", "3:00 pm", "15:00"
 */
export function normalizeTimeFormat(timeStr: string): string {
  if (!timeStr) return '';
  
  let normalized = timeStr.trim();
  
  // Replace narrow non-breaking spaces (\u202f) and other special whitespace with regular spaces
  normalized = normalized.replace(/[\u202f\u00a0\u2000-\u200b]/g, ' ');
  
  // Replace en-dash (–) and em-dash (—) with regular hyphen
  normalized = normalized.replace(/[\u2013\u2014]/g, '-');
  
  // Remove extra whitespace
  normalized = normalized.replace(/\s+/g, ' ').trim();
  
  // Check for 24-hour format (HH:MM without AM/PM)
  const twentyFourHourMatch = normalized.match(/^(\d{1,2}):(\d{2})$/);
  if (twentyFourHourMatch) {
    let hours = parseInt(twentyFourHourMatch[1], 10);
    const minutes = twentyFourHourMatch[2];
    
    if (hours >= 0 && hours <= 23) {
      const period = hours >= 12 ? 'PM' : 'AM';
      if (hours === 0) hours = 12;
      else if (hours > 12) hours -= 12;
      return `${hours}:${minutes} ${period}`;
    }
  }
  
  // Handle formats with AM/PM
  // Match patterns like "3pm", "3:00pm", "3:00 pm", "3:00  PM", "3 PM", "3PM"
  const ampmMatch = normalized.match(/^(\d{1,2})(?::(\d{2}))?\s*(am|pm|AM|PM|a\.m\.|p\.m\.|A\.M\.|P\.M\.)/i);
  
  if (ampmMatch) {
    let hours = parseInt(ampmMatch[1], 10);
    const minutes = ampmMatch[2] || '00';
    const period = ampmMatch[3].toUpperCase().replace(/\./g, '').replace('M', 'M');
    
    // Normalize period
    const normalizedPeriod = period.startsWith('A') ? 'AM' : 'PM';
    
    return `${hours}:${minutes.padStart(2, '0')} ${normalizedPeriod}`;
  }
  
  // If already in standard format, return as-is
  return normalized;
}

/**
 * Parse time with flexible format, normalizing first
 */
export function parseFlexibleTime(timeStr: string): number {
  const normalized = normalizeTimeFormat(timeStr);
  return parseTimeToMinutes(normalized);
}

/**
 * Preprocess happy hour string to add spaces between concatenated days
 * e.g., "Monday: 3-6pmTuesday: 3-6pm" -> "Monday: 3-6pm | Tuesday: 3-6pm"
 */
function preprocessHappyHourString(happyHourString: string): string {
  // Replace narrow non-breaking spaces and other special chars first
  let processed = happyHourString.replace(/[\u202f\u00a0\u2000-\u200b]/g, ' ');
  processed = processed.replace(/[\u2013\u2014]/g, '-');
  
  // Insert separator before day names that are directly attached to previous content
  // Match patterns like "6 pmTuesday", "6PMTuesday", "ClosedTuesday", "11:00PMTuesday"
  const dayNames = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'];
  
  for (const day of dayNames) {
    // Match day name preceded by a letter, number, or M (from AM/PM)
    // This handles: "pmTuesday", "PMTuesday", "6PMTuesday", "8:00PMTuesday"
    const regex = new RegExp(`([a-zA-Z0-9])(${day}:)`, 'gi');
    processed = processed.replace(regex, '$1 | $2');
  }
  
  return processed;
}

/**
 * Normalize an entire happy hour times string
 * Converts "Monday: 3pm-6pm | Tuesday: 4:00PM-7:00PM" to consistent format
 */
export function normalizeHappyHourTimes(happyHourString: string): string {
  if (!happyHourString || happyHourString.trim() === "") {
    return "";
  }

  // First preprocess to fix missing spaces between days
  const preprocessed = preprocessHappyHourString(happyHourString);
  
  // Normalize dashes in time separators (5:00PM-8:00PM -> 5:00PM - 8:00PM)
  const dashNormalized = preprocessed.replace(/([apAP][mM])-+(\d)/g, '$1 - $2');
  
  const dayEntries = dashNormalized.split(" | ");
  const normalizedEntries: string[] = [];

  for (const entry of dayEntries) {
    const trimmedEntry = entry.trim();
    if (!trimmedEntry) continue;
    
    const colonIndex = trimmedEntry.indexOf(': ');
    if (colonIndex === -1) {
      normalizedEntries.push(trimmedEntry);
      continue;
    }
    
    const dayName = trimmedEntry.substring(0, colonIndex).trim();
    const timeRange = trimmedEntry.substring(colonIndex + 2).trim();
    
    if (!dayName || !timeRange) {
      normalizedEntries.push(trimmedEntry);
      continue;
    }

    if (timeRange.toLowerCase() === "closed") {
      normalizedEntries.push(`${dayName}: Closed`);
      continue;
    }

    // Handle multiple sessions separated by comma
    const sessions = timeRange.split(", ");
    const normalizedSessions: string[] = [];

    for (const session of sessions) {
      // Normalize dashes in session
      const sessionNormalized = session.replace(/-+/g, ' - ').replace(/\s+/g, ' ').trim();
      const times = sessionNormalized.split(" - ");
      if (times.length !== 2) {
        normalizedSessions.push(sessionNormalized);
        continue;
      }

      const startTime = normalizeTimeFormat(times[0].trim());
      const endTime = normalizeTimeFormat(times[1].trim());
      normalizedSessions.push(`${startTime} - ${endTime}`);
    }

    normalizedEntries.push(`${dayName}: ${normalizedSessions.join(", ")}`);
  }

  return normalizedEntries.join(" | ");
}
