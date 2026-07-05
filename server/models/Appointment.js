import mongoose from "mongoose";
const appointmentSchema = new mongoose.Schema(
    {
        name: String,
        doctor: String,
        date: String,
        time: String,
        status: { type: String, default: "booked" }
    },
    { timestamps: true });
export default mongoose.model("Appointment", appointmentSchema);