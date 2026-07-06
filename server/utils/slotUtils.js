const SLOT_DURATION_MINUTES = 60;

export function parseTimeToMinutes(time) {
    const match = String(time).trim().match(/^(\d{1,2}):(\d{2})$/);
    if (!match) return null;

    const hours = Number(match[1]);
    const minutes = Number(match[2]);
    if (hours < 0 || hours > 23 || minutes < 0 || minutes > 59) return null;

    return hours * 60 + minutes;
}

export function formatMinutesToTime(totalMinutes) {
    const hours = Math.floor(totalMinutes / 60);
    const minutes = totalMinutes % 60;
    return `${String(hours).padStart(2, "0")}:${String(minutes).padStart(2, "0")}`;
}

export function validateSlotTime(time) {
    const minutes = parseTimeToMinutes(time);
    if (minutes === null) {
        return { valid: false, message: "Time must be HH:MM in 24-hour format (e.g. 09:00, 14:00)" };
    }
    if (minutes % SLOT_DURATION_MINUTES !== 0) {
        return {
            valid: false,
            message: "Each appointment is a 1-hour slot starting on the hour (e.g. 09:00, 10:00, 14:00)",
        };
    }
    if (minutes + SLOT_DURATION_MINUTES > 24 * 60) {
        return { valid: false, message: "Last bookable slot is 23:00 (1-hour appointment)" };
    }

    return { valid: true, minutes, normalizedTime: formatMinutesToTime(minutes) };
}

export function slotsOverlap(startA, startB, duration = SLOT_DURATION_MINUTES) {
    return startA < startB + duration && startA + duration > startB;
}

export function findConflictingAppointment(appointments, requestedMinutes) {
    return appointments.find((appointment) => {
        const existingMinutes = parseTimeToMinutes(appointment.time);
        if (existingMinutes === null) return false;
        return slotsOverlap(requestedMinutes, existingMinutes);
    });
}
