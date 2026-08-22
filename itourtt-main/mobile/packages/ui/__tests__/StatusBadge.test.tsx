import React from 'react';
import { render } from '@testing-library/react-native';
import { StatusBadge } from '../src/StatusBadge';

describe('StatusBadge', () => {
  const statuses = ['PENDING', 'ASSIGNED', 'IN_PROGRESS', 'COMPLETED', 'CANCELLED', 'NO_SHOW'] as const;

  it('renders without crashing for all statuses', () => {
    statuses.forEach((status) => {
      const { unmount } = render(<StatusBadge status={status} />);
      unmount();
    });
  });

  it('renders the translated status label for PENDING', () => {
    const { getByText } = render(<StatusBadge status="PENDING" />);
    // The mock t() returns the key, so it should render 'status.PENDING'
    expect(getByText('status.PENDING')).toBeTruthy();
  });

  it('renders the translated status label for COMPLETED', () => {
    const { getByText } = render(<StatusBadge status="COMPLETED" />);
    expect(getByText('status.COMPLETED')).toBeTruthy();
  });

  it('renders the translated status label for IN_PROGRESS', () => {
    const { getByText } = render(<StatusBadge status="IN_PROGRESS" />);
    expect(getByText('status.IN_PROGRESS')).toBeTruthy();
  });

  it('renders the translated status label for CANCELLED', () => {
    const { getByText } = render(<StatusBadge status="CANCELLED" />);
    expect(getByText('status.CANCELLED')).toBeTruthy();
  });

  it('renders the translated status label for NO_SHOW', () => {
    const { getByText } = render(<StatusBadge status="NO_SHOW" />);
    expect(getByText('status.NO_SHOW')).toBeTruthy();
  });

  it('renders the translated status label for ASSIGNED', () => {
    const { getByText } = render(<StatusBadge status="ASSIGNED" />);
    expect(getByText('status.ASSIGNED')).toBeTruthy();
  });

  it('applies correct background color for PENDING status', () => {
    const { UNSAFE_getAllByType } = render(<StatusBadge status="PENDING" />);
    const { View } = require('react-native');
    const views = UNSAFE_getAllByType(View);
    // The Badge wraps in a View - find the one with backgroundColor
    const badgeView = views.find((v: any) => {
      const flatStyle = Array.isArray(v.props.style)
        ? Object.assign({}, ...v.props.style.filter(Boolean))
        : v.props.style;
      return flatStyle?.backgroundColor;
    });
    expect(badgeView).toBeTruthy();
    const flatStyle = Array.isArray(badgeView!.props.style)
      ? Object.assign({}, ...badgeView!.props.style.filter(Boolean))
      : badgeView!.props.style;
    expect(flatStyle.backgroundColor).toBe('#fef2f2');
  });

  it('applies correct background color for COMPLETED status', () => {
    const { UNSAFE_getAllByType } = render(<StatusBadge status="COMPLETED" />);
    const { View } = require('react-native');
    const views = UNSAFE_getAllByType(View);
    const badgeView = views.find((v: any) => {
      const flatStyle = Array.isArray(v.props.style)
        ? Object.assign({}, ...v.props.style.filter(Boolean))
        : v.props.style;
      return flatStyle?.backgroundColor;
    });
    expect(badgeView).toBeTruthy();
    const flatStyle = Array.isArray(badgeView!.props.style)
      ? Object.assign({}, ...badgeView!.props.style.filter(Boolean))
      : badgeView!.props.style;
    expect(flatStyle.backgroundColor).toBe('#f0fdf4');
  });

  it('falls back to PENDING colors for unknown status', () => {
    const { getByText } = render(<StatusBadge status={'UNKNOWN' as any} />);
    expect(getByText('status.UNKNOWN')).toBeTruthy();
  });
});
