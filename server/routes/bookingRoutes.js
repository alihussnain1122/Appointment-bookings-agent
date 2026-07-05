import express from "express";
import { 
    checkAvailability, 
    bookAppointment, 
    cancelAppointment, } from "../controllers/bookingController.js";
    
const router = express.Router();


router.post("/check-availability", checkAvailability);
router.post("/book", bookAppointment);
router.post("/cancel", cancelAppointment);
export default router;