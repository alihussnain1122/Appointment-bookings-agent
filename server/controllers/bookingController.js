import Appointment from "../models/Appointment.js";
import { addToSheet } from "../services/googleSheet.js";

const activeSlotQuery = (doctor, date, time) => ({
    doctor,
    date,
    time,
    status: { $ne: "cancelled" },
});

export const checkAvailability = async (req, res) => {
    try {
        const { doctor, date, time } = req.body;
        if (!doctor || !date || !time) {
            return res.status(400).json({ message: "doctor, date, and time are required" });
        }
        const existing = await Appointment.findOne(activeSlotQuery(doctor, date, time));
        return res.json({ available: !existing });
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
        const exists = await Appointment.findOne(activeSlotQuery(doctor, date, time));
        if (exists) {
            return res.status(400).json({ message: "Slot already booked" });
        }
        const appointment = await Appointment.create({ name, doctor, date, time });
        if (process.env.GOOGLE_SHEET_ID) {
            try {
                await addToSheet({ name, doctor, date, time, status: "Booked" });
            } catch (sheetError) {
                console.error("Google Sheets sync failed:", sheetError.message);
            }
        }
        res.json({ message: "Appointment booked successfully", appointment });
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
