import React from 'react';
import { render } from '@testing-library/react-native';
import { Text } from 'react-native';
import { EmptyState } from '../src/EmptyState';

describe('EmptyState', () => {
  it('renders the title', () => {
    const { getByText } = render(<EmptyState title="No Jobs Found" />);
    expect(getByText('No Jobs Found')).toBeTruthy();
  });

  it('renders the message when provided', () => {
    const { getByText } = render(
      <EmptyState title="No Jobs" message="There are no jobs for this date." />,
    );
    expect(getByText('There are no jobs for this date.')).toBeTruthy();
  });

  it('does not render message when not provided', () => {
    const { queryByText } = render(<EmptyState title="No Jobs" />);
    // Only the title should be present
    expect(queryByText('There are no jobs')).toBeNull();
  });

  it('renders icon when provided', () => {
    const icon = <Text testID="empty-icon">icon</Text>;
    const { getByTestId } = render(
      <EmptyState title="No Jobs" icon={icon} />,
    );
    expect(getByTestId('empty-icon')).toBeTruthy();
  });

  it('does not crash when icon is not provided', () => {
    const { getByText } = render(<EmptyState title="No Data" />);
    expect(getByText('No Data')).toBeTruthy();
  });

  it('renders action when provided', () => {
    const action = <Text testID="action-button">Retry</Text>;
    const { getByTestId, getByText } = render(
      <EmptyState title="Error" action={action} />,
    );
    expect(getByTestId('action-button')).toBeTruthy();
    expect(getByText('Retry')).toBeTruthy();
  });

  it('does not render action slot when not provided', () => {
    const { queryByTestId } = render(<EmptyState title="Empty" />);
    expect(queryByTestId('action-button')).toBeNull();
  });

  it('renders title, message, icon, and action all together', () => {
    const icon = <Text testID="icon">Icon</Text>;
    const action = <Text testID="action">Refresh</Text>;
    const { getByText, getByTestId } = render(
      <EmptyState
        title="All Clear"
        message="Nothing to see here"
        icon={icon}
        action={action}
      />,
    );
    expect(getByText('All Clear')).toBeTruthy();
    expect(getByText('Nothing to see here')).toBeTruthy();
    expect(getByTestId('icon')).toBeTruthy();
    expect(getByTestId('action')).toBeTruthy();
  });
});
