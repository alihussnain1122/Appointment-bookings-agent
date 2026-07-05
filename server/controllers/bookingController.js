import Appointment from "../models/Appointment.js";
import { addToSheet } from "../services/googleSheets.js";
// Check Availability
export const checkAvailability = async (req, res) => {
    const { doctor, date, time } = req.body;
    const existing = await Appointment.findOne(
        { doctor, date, time });
    if (existing) {
        return res.json({ available: false });
    } return res.json({ available: true });
};
// Book Appointment
export const bookAppointment = async (req, res) => {
    try {
        const
        { name, doctor, date, time } = req.body;
        const exists = await Appointment.findOne({
            doctor, date, time

        }); if (exists) {
            return res.status(400).json({ message: "Slot already booked" });
        } const appointment = await Appointment.create({
            name, doctor, date, time,
        });
        // Add to Google Sheets
        await addToSheet({ name, doctor, date, time, status: "Booked", });
        res.json({ message: "Appointment booked successfully", appointment, });
    }
    catch (error) {
        res.status(500).json({ message: error.message });
    }
};
// Cancel Appointment
export const cancelAppointment = async (req, res) => {
    const { id } = req.body;
    const appointment = await Appointment.findById(id);
    if (!appointment) { return res.status(404).json({ message: "Not found" }); }
    appointment.status = "cancelled";
    await appointment.save();
    res.json({ message: "Appointment cancelled" });
};