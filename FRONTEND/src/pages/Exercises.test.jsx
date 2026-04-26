import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import Exercises from './Exercises.jsx';

vi.mock('react-speech-recognition', () => {
  const initialState = {
    transcript: '',
    listening: false,
    browserSupportsSpeechRecognition: true,
    isMicrophoneAvailable: true,
  };

  let state = { ...initialState };

  const startListening = vi.fn(async () => {
    state = { ...state, listening: true };
  });
  const stopListening = vi.fn(async () => {
    state = { ...state, listening: false };
  });
  const resetTranscript = vi.fn(() => {
    state = { ...state, transcript: '' };
  });
  const setMockState = (patch) => {
    state = { ...state, ...patch };
  };
  const resetMock = () => {
    state = { ...initialState };
    startListening.mockClear();
    stopListening.mockClear();
    resetTranscript.mockClear();
  };

  return {
    default: {
      startListening,
      stopListening,
    },
    useSpeechRecognition: () => ({
      ...state,
      resetTranscript,
    }),
    __setMockState: setMockState,
    __resetMockState: resetMock,
    __mocks: {
      startListening,
      stopListening,
    },
  };
});

import * as speechModule from 'react-speech-recognition';

describe('Exercises voice counting', () => {
  beforeEach(() => {
    speechModule.__resetMockState();
  });

  it('starts and stops session', async () => {
    const { rerender } = render(<Exercises />);

    fireEvent.click(screen.getByRole('button', { name: 'Začít poslouchat' }));
    rerender(<Exercises />);
    expect(speechModule.__mocks.startListening).toHaveBeenCalledTimes(1);
    expect(screen.getByText(/Stav relace: listening/)).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: 'Zastavit počítání' }));
    expect(speechModule.__mocks.stopListening).toHaveBeenCalledTimes(1);
    await waitFor(() => expect(screen.getByText(/Stav relace:\s*stopped/)).toBeInTheDocument());
  });

  it('updates number and event list from transcript', async () => {
    const { rerender } = render(<Exercises />);

    fireEvent.click(screen.getByRole('button', { name: 'Začít poslouchat' }));
    speechModule.__setMockState({ transcript: 'ahoj 7 7' });
    rerender(<Exercises />);

    expect(screen.getByText('Aktuální číslo')).toBeInTheDocument();
    expect(screen.getByText(/7 \(7\)/)).toBeInTheDocument();
    expect(screen.getByText('Rozpoznáno čísel')).toBeInTheDocument();
    expect(screen.getByText('Události (1)')).toBeInTheDocument();
  });

  it('ignores non-number transcript', () => {
    const { rerender } = render(<Exercises />);

    fireEvent.click(screen.getByRole('button', { name: 'Začít poslouchat' }));
    speechModule.__setMockState({ transcript: 'ahoj svete' });
    rerender(<Exercises />);

    expect(screen.getByText('Události (0)')).toBeInTheDocument();
  });

  it('resets session data', async () => {
    const { rerender } = render(<Exercises />);

    fireEvent.click(screen.getByRole('button', { name: 'Začít poslouchat' }));
    speechModule.__setMockState({ transcript: '8' });
    rerender(<Exercises />);
    expect(screen.getByText('Události (1)')).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: 'Nová relace' }));
    rerender(<Exercises />);
    await waitFor(() => expect(screen.getByText('Události (0)')).toBeInTheDocument());
  });

  it('shows unsupported browser fallback', () => {
    speechModule.__setMockState({ browserSupportsSpeechRecognition: false });
    render(<Exercises />);

    expect(screen.getByText(/nepodporuje rozpoznávání řeči/i)).toBeInTheDocument();
  });

  it('shows microphone permission error', async () => {
    const { rerender } = render(<Exercises />);

    speechModule.__setMockState({
      browserSupportsSpeechRecognition: true,
      isMicrophoneAvailable: false,
    });
    fireEvent.click(screen.getByRole('button', { name: 'Začít poslouchat' }));
    rerender(<Exercises />);
    await waitFor(() => expect(screen.getByText(/Mikrofon není dostupný/i)).toBeInTheDocument());
  });
});
