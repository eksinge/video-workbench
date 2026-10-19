// An original, deterministic synth bed. No downloaded samples or external assets.
import {writeFileSync, mkdirSync} from 'node:fs';
const rate = 48000;
const seconds = 15;
const count = rate * seconds;
const buffer = Buffer.alloc(44 + count * 4);
buffer.write('RIFF'); buffer.writeUInt32LE(buffer.length - 8, 4); buffer.write('WAVE', 8);
buffer.write('fmt ', 12); buffer.writeUInt32LE(16, 16); buffer.writeUInt16LE(1, 20);
buffer.writeUInt16LE(2, 22); buffer.writeUInt32LE(rate, 24); buffer.writeUInt32LE(rate * 4, 28);
buffer.writeUInt16LE(4, 32); buffer.writeUInt16LE(16, 34); buffer.write('data', 36); buffer.writeUInt32LE(count * 4, 40);
const notes = [220, 277.1826, 329.6276, 415.3047, 329.6276, 277.1826, 246.9417, 329.6276];
for (let i = 0; i < count; i++) {
  const t = i / rate;
  const beat = t % 0.5;
  const index = Math.floor(t / 0.5) % notes.length;
  const note = notes[index];
  const pluck = Math.exp(-beat * 9) * Math.min(1, beat * 150) * (Math.sin(2 * Math.PI * note * beat) * 0.13 + Math.sin(2 * Math.PI * note * 2 * beat) * 0.025);
  const kick = Math.sin(2 * Math.PI * (49 * beat + 1.1 * (1 - Math.exp(-beat * 30)))) * Math.exp(-beat * 17) * 0.13;
  const pad = (Math.sin(2 * Math.PI * 110 * t) + Math.sin(2 * Math.PI * 164.8138 * t) + Math.sin(2 * Math.PI * 207.6523 * t)) * 0.023;
  const fade = Math.min(1, t / 0.3, (seconds - t) / 1.1);
  for (let channel = 0; channel < 2; channel++) {
    const stereo = 1 + Math.sin(t * 0.7 + channel * Math.PI) * 0.09;
    const value = Math.tanh((pluck * stereo + kick + pad) * fade);
    buffer.writeInt16LE(Math.round(value * 32767), 44 + i * 4 + channel * 2);
  }
}
mkdirSync(new URL('../public/', import.meta.url), {recursive: true});
writeFileSync(new URL('../public/launch.wav', import.meta.url), buffer);
console.log('Created original 15-second stereo synth bed.');
