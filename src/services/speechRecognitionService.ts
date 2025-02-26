import { createReadStream } from 'fs';
import { SpeechClient } from '@google-cloud/speech';
import { Readable } from 'stream';

export class SpeechRecognitionService {
    private client: SpeechClient;

    constructor() {
        this.client = new SpeechClient();
    }

    public async startRecognition(file: File): Promise<string> {
        const audioStream = this.createAudioStream(file);
        const request = {
            audio: {
                content: await this.streamToBuffer(audioStream),
            },
            config: {
                encoding: 'LINEAR16',
                sampleRateHertz: 16000,
                languageCode: 'en-US',
            },
        };

        const [response] = await this.client.recognize(request);
        const transcription = response.results
            .map(result => result.alternatives[0].transcript)
            .join('\n');

        return transcription;
    }

    private createAudioStream(file: File): Readable {
        return createReadStream(file.path);
    }

    private streamToBuffer(stream: Readable): Promise<Buffer> {
        return new Promise((resolve, reject) => {
            const chunks: Buffer[] = [];
            stream.on('data', chunk => chunks.push(Buffer.from(chunk)));
            stream.on('end', () => resolve(Buffer.concat(chunks)));
            stream.on('error', reject);
        });
    }
}