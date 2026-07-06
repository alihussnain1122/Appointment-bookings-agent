import Appointment from "../models/Appointment.js";
import { addToSheet } from "../services/googleSheet.js";
import {
    findConflictingAppointment,
    validateSlotTime,
} from "../utils/slotUtils.js";

const getActiveAppointments = (doctor, date) =>
    Appointment.find({ doctor, date, status: { $ne: "cancelled" } });

export const checkAvailability = async (req, res) => {
    try {
        const { doctor, date, time } = req.body;
        if (!doctor || !date || !time) {
            return res.status(400).json({ message: "doctor, date, and time are required" });
        }

        const slot = validateSlotTime(time);
        if (!slot.valid) {
            return res.status(400).json({ message: slot.message, available: false });
        }

        const appointments = await getActiveAppointments(doctor, date);
        const conflict = findConflictingAppointment(appointments, slot.minutes);

        return res.json({
            available: !conflict,
            slotDurationMinutes: 60,
            normalizedTime: slot.normalizedTime,
            ...(conflict && {
                reason: `Conflicts with existing booking at ${conflict.time}`,
            }),
        });
    } catch (error) {
        res.status(500).json({ message: error.message });
    }
};

export const bookAppointment = async (req, res) => {
    try {
        const { name, doctor, date, time } = req.body;
        if (!name || !doctor || !date || !time) {
            return res.status(400).json({ message: "name, doctor, date, and time are required" });
        }

        const slot = validateSlotTime(time);
        if (!slot.valid) {
            return res.status(400).json({ message: slot.message });
        }

        const appointments = await getActiveAppointments(doctor, date);
        const conflict = findConflictingAppointment(appointments, slot.minutes);
        if (conflict) {
            return res.status(400).json({
                message: `Slot not available. ${doctor} already has a 1-hour appointment at ${conflict.time} on ${date}.`,
            });
        }

        const appointment = await Appointment.create({
            name,
            doctor,
            date,
            time: slot.normalizedTime,
        });

        if (process.env.GOOGLE_SHEET_ID) {
            try {
                await addToSheet({
                    name,
                    doctor,
                    date,
                    time: slot.normalizedTime,
                    status: "Booked",
                });
            } catch (sheetError) {
                console.error("Google Sheets sync failed:", sheetError.message);
            }
        }

        res.json({
            message: "Appointment booked successfully",
            slotDurationMinutes: 60,
            appointment,
        });
    } catch (error) {
        res.status(500).json({ message: error.message });
    }
};

export const cancelAppointment = async (req, res) => {
    try {
        const { id } = req.body;
        if (!id) {
            return res.status(400).json({ message: "id is required" });
        }
        const appointment = await Appointment.findById(id);
        if (!appointment) {
            return res.status(404).json({ message: "Not found" });
        }
        if (appointment.status === "cancelled") {
            return res.status(400).json({ message: "Appointment already cancelled" });
        }
        appointment.status = "cancelled";
        await appointment.save();
        res.json({ message: "Appointment cancelled", appointment });
    } catch (error) {
        res.status(500).json({ message: error.message });
    }
};
