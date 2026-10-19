import {z} from 'zod';

export const launchSchema = z.object({
  projectName: z.string().min(1).max(16),
  eyebrow: z.string().max(24),
  headlineLine1: z.string().max(10),
  headlineLine2: z.string().max(10),
  description: z.string().max(36),
  featureOne: z.string().max(10),
  featureTwo: z.string().max(10),
  featureThree: z.string().max(10),
  closingTitle: z.string().max(16),
  callToAction: z.string().max(16),
  footer: z.string().max(60),
  accent: z.string().regex(/^#[0-9a-fA-F]{6}$/),
  music: z.boolean(),
});

export type LaunchProps = z.infer<typeof launchSchema>;
