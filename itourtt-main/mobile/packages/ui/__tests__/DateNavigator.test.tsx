import React from 'react';
import { render, fireEvent } from '@testing-library/react-native';
import { DateNavigator } from '../src/DateNavigator';

// Note: The @itour/shared mock in jest.setup.ts provides:
// - formatDate: identity function (returns the date string as-is)
// - addDays: functional mock that computes the correct date
// - today: returns '2026-02-20'
// - useT: returns (key) => key

describe('DateNavigator', () => {
  const defaultProps = {
    date: '2026-02-20',
    onDateChange: jest.fn(),
  };

  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('renders the current date', () => {
    const { getByText } = render(<DateNavigator {...defaultProps} />);
    // formatDate mock returns the string as-is
    expect(getByText('2026-02-20')).toBeTruthy();
  });

  it('renders left arrow for previous day', () => {
    const { getByText } = render(<DateNavigator {...defaultProps} />);
    // Left arrow character
    expect(getByText('\u2039')).toBeTruthy();
  });

  it('renders right arrow for next day', () => {
    const { getByText } = render(<DateNavigator {...defaultProps} />);
    // Right arrow character
    expect(getByText('\u203A')).toBeTruthy();
  });

  it('calls onDateChange with previous day when left arrow is pressed', () => {
    const onDateChange = jest.fn();
    const { getByText } = render(
      <DateNavigator date="2026-02-20" onDateChange={onDateChange} />,
    );
    fireEvent.press(getByText('\u2039'));
    expect(onDateChange).toHaveBeenCalledWith('2026-02-19');
  });

  it('calls onDateChange with next day when right arrow is pressed', () => {
    const onDateChange = jest.fn();
    const { getByText } = render(
      <DateNavigator date="2026-02-20" onDateChange={onDateChange} />,
    );
    fireEvent.press(getByText('\u203A'));
    expect(onDateChange).toHaveBeenCalledWith('2026-02-21');
  });

  it('calls onDateChange with today when center date is pressed', () => {
    const onDateChange = jest.fn();
    const { getByText } = render(
      <DateNavigator date="2026-02-18" onDateChange={onDateChange} />,
    );
    // Press the date text itself (which is the center touchable)
    fireEvent.press(getByText('2026-02-18'));
    expect(onDateChange).toHaveBeenCalledWith('2026-02-20');
  });

  it('shows "Today" label when date is not today', () => {
    const { getByText } = render(
      <DateNavigator date="2026-02-18" onDateChange={jest.fn()} />,
    );
    // useT mock returns the key, so 'common.today' is rendered
    expect(getByText('common.today')).toBeTruthy();
  });

  it('does not show "Today" label when date IS today', () => {
    const { queryByText } = render(
      <DateNavigator date="2026-02-20" onDateChange={jest.fn()} />,
    );
    expect(queryByText('common.today')).toBeNull();
  });

  it('handles month boundary correctly (going backward from March 1)', () => {
    const onDateChange = jest.fn();
    const { getByText } = render(
      <DateNavigator date="2026-03-01" onDateChange={onDateChange} />,
    );
    fireEvent.press(getByText('\u2039'));
    expect(onDateChange).toHaveBeenCalledWith('2026-02-28');
  });
});
