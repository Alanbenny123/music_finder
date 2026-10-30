import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import axios from 'axios';
import App from './App';

jest.mock('axios', () => ({ get: jest.fn(), post: jest.fn() }));

beforeEach(() => {
  axios.get.mockReset();
  axios.post.mockReset();
});

test('uploads a selected file through the API and shows its stems', async () => {
  axios.get.mockResolvedValue({ data: { status: 'healthy' } });
  axios.post.mockResolvedValue({
    data: { tracks: { vocals: '/api/download/job-id/vocals' } },
  });

  const { container } = render(<App />);
  const start = screen.getByRole('button', { name: /start separation/i });
  expect(start).toBeDisabled();

  const file = new File(['audio'], 'song.mp3', { type: 'audio/mpeg' });
  fireEvent.change(container.querySelector('input[type="file"]'), {
    target: { files: [file] },
  });
  fireEvent.click(start);

  await screen.findByText('Separated Tracks');
  expect(screen.getByText('Vocals')).toBeInTheDocument();
  expect(axios.get).toHaveBeenCalledWith('/health');
  expect(axios.post).toHaveBeenCalledWith(
    '/api/separate',
    expect.any(FormData),
    expect.any(Object)
  );
});

test('shows a backend error after upload fails', async () => {
  axios.get.mockResolvedValue({ data: { status: 'healthy' } });
  axios.post.mockRejectedValue({ response: { data: { error: 'Invalid audio' } } });

  const { container } = render(<App />);
  fireEvent.change(container.querySelector('input[type="file"]'), {
    target: { files: [new File(['audio'], 'song.mp3')] },
  });
  fireEvent.click(screen.getByRole('button', { name: /start separation/i }));

  await waitFor(() => expect(screen.getByRole('alert')).toHaveTextContent('Invalid audio'));
});
