import { Request, Response } from 'express';
import { SpeechRecognitionService } from '../services/speechRecognitionService';

export class AudioController {
    private speechRecognitionService: SpeechRecognitionService;

    constructor() {
        this.speechRecognitionService = new SpeechRecognitionService();
    }

    public async uploadAudio(req: Request, res: Response): Promise<void> {
        try {
            const audioFile = req.file; // Assuming you're using multer for file uploads
            if (!audioFile) {
                res.status(400).send('No audio file uploaded.');
                return;
            }

            const transcription = await this.speechRecognitionService.startRecognition(audioFile);
            res.status(200).json({ transcription });
        } catch (error) {
            res.status(500).send('Error processing audio file.');
        }
    }
}