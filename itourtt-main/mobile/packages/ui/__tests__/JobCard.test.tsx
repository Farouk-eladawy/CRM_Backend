import React from 'react';
import { render, fireEvent } from '@testing-library/react-native';
import { JobCard } from '../src/JobCard';
import type { PortalJob } from '@itour/shared';

// Mock the ServiceTypeBadge and StatusBadge since they depend on @itour/shared
jest.mock('../src/ServiceTypeBadge', () => ({
  ServiceTypeBadge: ({ serviceType }: { serviceType: string }) => {
    const { Text } = require('react-native');
    return <Text testID="service-type-badge">{serviceType}</Text>;
  },
}));

jest.mock('../src/StatusBadge', () => ({
  StatusBadge: ({ status }: { status: string }) => {
    const { Text } = require('react-native');
    return <Text testID="status-badge">{status}</Text>;
  },
}));

const createMockJob = (overrides: Partial<PortalJob> = {}): PortalJob => ({
  id: 'job-1',
  internalRef: 'TF-2026-0001',
  serviceType: 'ARR',
  jobDate: '2026-02-20',
  status: 'ASSIGNED',
  paxCount: 3,
  clientName: 'John Smith',
  clientMobile: '+20123456789',
  pickUpTime: null,
  notes: null,
  originAirport: { id: 'a1', name: 'Cairo Airport', code: 'CAI' },
  destinationHotel: { id: 'h1', name: 'Marriott' },
  flight: {
    id: 'f1',
    trafficJobId: 'job-1',
    flightNo: 'MS801',
    carrier: 'EgyptAir',
    terminal: 'T2',
    arrivalTime: '2026-02-20T14:30:00Z',
    departureTime: null,
  },
  ...overrides,
});

describe('JobCard', () => {
  const defaultProps = {
    job: createMockJob(),
  };

  it('renders the job internal reference', () => {
    const { getByText } = render(<JobCard {...defaultProps} />);
    expect(getByText('TF-2026-0001')).toBeTruthy();
  });

  it('renders the route info', () => {
    const { getByText } = render(<JobCard {...defaultProps} />);
    // The mock getRouteLabel returns a fixed string
    expect(getByText('Cairo Airport (CAI) \u2192 Sharm El Sheikh')).toBeTruthy();
  });

  it('renders the service type badge', () => {
    const { getByTestId } = render(<JobCard {...defaultProps} />);
    expect(getByTestId('service-type-badge')).toBeTruthy();
  });

  it('renders the status badge', () => {
    const { getByTestId } = render(<JobCard {...defaultProps} />);
    expect(getByTestId('status-badge')).toBeTruthy();
  });

  it('renders pax count', () => {
    const { getByText } = render(<JobCard {...defaultProps} />);
    expect(getByText('3 pax')).toBeTruthy();
  });

  it('renders flight number when available', () => {
    const { getByText } = render(<JobCard {...defaultProps} />);
    expect(getByText('MS801')).toBeTruthy();
  });

  it('renders client name when available', () => {
    const { getByText } = render(<JobCard {...defaultProps} />);
    expect(getByText('John Smith')).toBeTruthy();
  });

  it('does not render client name when it is null', () => {
    const job = createMockJob({ clientName: null });
    const { queryByText } = render(<JobCard job={job} />);
    expect(queryByText('John Smith')).toBeNull();
  });

  it('renders time from flight arrival time', () => {
    const { getByText } = render(<JobCard {...defaultProps} />);
    // formatTime mock returns the string as-is
    expect(getByText('2026-02-20T14:30:00Z')).toBeTruthy();
  });

  it('renders pickUpTime when no flight arrival time', () => {
    const job = createMockJob({
      flight: undefined,
      pickUpTime: '2026-02-20T10:00:00Z',
    });
    const { getByText } = render(<JobCard job={job} />);
    expect(getByText('2026-02-20T10:00:00Z')).toBeTruthy();
  });

  describe('onPress', () => {
    it('calls onPress when tapped', () => {
      const onPress = jest.fn();
      const { getByText } = render(<JobCard {...defaultProps} onPress={onPress} />);
      fireEvent.press(getByText('TF-2026-0001'));
      expect(onPress).toHaveBeenCalledTimes(1);
    });

    it('is disabled when no onPress provided', () => {
      const { UNSAFE_getByType } = render(<JobCard {...defaultProps} />);
      const { TouchableOpacity } = require('react-native');
      const touchable = UNSAFE_getByType(TouchableOpacity);
      expect(touchable.props.disabled).toBe(true);
    });

    it('is enabled when onPress is provided', () => {
      const { UNSAFE_getByType } = render(
        <JobCard {...defaultProps} onPress={jest.fn()} />,
      );
      const { TouchableOpacity } = require('react-native');
      const touchable = UNSAFE_getByType(TouchableOpacity);
      expect(touchable.props.disabled).toBe(false);
    });
  });

  describe('portalStatus override', () => {
    it('uses portalStatus when provided', () => {
      const { getByTestId } = render(
        <JobCard {...defaultProps} portalStatus="COMPLETED" />,
      );
      const statusBadge = getByTestId('status-badge');
      expect(statusBadge.props.children).toBe('COMPLETED');
    });

    it('falls back to job.status when portalStatus is not provided', () => {
      const { getByTestId } = render(<JobCard {...defaultProps} />);
      const statusBadge = getByTestId('status-badge');
      expect(statusBadge.props.children).toBe('ASSIGNED');
    });
  });

  describe('optional content slots', () => {
    it('renders rightContent when provided', () => {
      const { Text } = require('react-native');
      const { getByText } = render(
        <JobCard
          {...defaultProps}
          rightContent={<Text>Right Content</Text>}
        />,
      );
      expect(getByText('Right Content')).toBeTruthy();
    });

    it('renders bottomContent when provided', () => {
      const { Text } = require('react-native');
      const { getByText } = render(
        <JobCard
          {...defaultProps}
          bottomContent={<Text>Bottom Content</Text>}
        />,
      );
      expect(getByText('Bottom Content')).toBeTruthy();
    });

    it('does not render right slot when rightContent is not provided', () => {
      const { queryByText } = render(<JobCard {...defaultProps} />);
      expect(queryByText('Right Content')).toBeNull();
    });
  });
});
