let displayTimezone = "Europe/Moscow";

const months = [
  "янв",
  "фев",
  "мар",
  "апр",
  "май",
  "июн",
  "июл",
  "авг",
  "сен",
  "окт",
  "ноя",
  "дек",
];

const TZ_SHORT: Record<string, string> = {
  "Europe/Moscow": "МСК",
  "Asia/Tehran": "IRST",
  UTC: "UTC",
};

export function setDisplayTimezone(tz: string) {
  displayTimezone = tz || "Europe/Moscow";
}

export function getDisplayTimezone() {
  return displayTimezone;
}

export function tzShort(tz = displayTimezone) {
  return TZ_SHORT[tz] ?? tz;
}

export function fmtMsk(iso: string | null | undefined, withTz = false): string {
  if (!iso) return "—";
  const d = new Date(iso);
  const parts = new Intl.DateTimeFormat("en-GB", {
    timeZone: displayTimezone,
    day: "numeric",
    month: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  }).formatToParts(d);
  const get = (type: string) => parts.find((p) => p.type === type)?.value ?? "";
  const day = get("day");
  const monthIdx = Number(get("month")) - 1;
  const hour = get("hour");
  const minute = get("minute");
  const base = `${day} ${months[monthIdx]}, ${hour}:${minute}`;
  return withTz ? `${base} ${tzShort()}` : base;
}

export function fmtTimeMsk(iso: string | null | undefined): string {
  if (!iso) return "—";
  return new Intl.DateTimeFormat("ru-RU", {
    timeZone: displayTimezone,
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  }).format(new Date(iso));
}

export function delayLabel(hours: number): string {
  if (!hours || hours <= 0) return "По плану";
  if (hours >= 12) return `△ +${Math.round(hours)} ч`;
  return `! +${Math.round(hours)} ч`;
}
