import { Router } from 'express';
import { AudioController } from '../controllers/audioController';

const router = Router();
const audioController = new AudioController();

export function setAudioRoutes(app: Express.Application) {
    app.use('/api/audio', router);
    router.post('/upload', audioController.uploadAudio.bind(audioController));
}