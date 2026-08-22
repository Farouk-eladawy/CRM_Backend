import React from 'react';
import { render } from '@testing-library/react-native';
import { Badge } from '../src/Badge';

describe('Badge', () => {
  const defaultProps = {
    label: 'Pending',
    backgroundColor: '#FEF2F2',
    textColor: '#DC2626',
  };

  it('renders the label text', () => {
    const { getByText } = render(<Badge {...defaultProps} />);
    expect(getByText('Pending')).toBeTruthy();
  });

  it('renders with the correct label', () => {
    const { getByText } = render(
      <Badge {...defaultProps} label="Completed" />,
    );
    expect(getByText('Completed')).toBeTruthy();
  });

  it('applies backgroundColor to the container', () => {
    const { UNSAFE_getByType } = render(<Badge {...defaultProps} />);
    const { View } = require('react-native');
    const view = UNSAFE_getByType(View);
    const flatStyle = Array.isArray(view.props.style)
      ? Object.assign({}, ...view.props.style.filter(Boolean))
      : view.props.style;
    expect(flatStyle.backgroundColor).toBe('#FEF2F2');
  });

  it('applies textColor to the text', () => {
    const { getByText } = render(<Badge {...defaultProps} />);
    const textEl = getByText('Pending');
    const flatStyle = Array.isArray(textEl.props.style)
      ? Object.assign({}, ...textEl.props.style.filter(Boolean))
      : textEl.props.style;
    expect(flatStyle.color).toBe('#DC2626');
  });

  it('uses backgroundColor as borderColor when borderColor is not provided', () => {
    const { UNSAFE_getByType } = render(<Badge {...defaultProps} />);
    const { View } = require('react-native');
    const view = UNSAFE_getByType(View);
    const flatStyle = Array.isArray(view.props.style)
      ? Object.assign({}, ...view.props.style.filter(Boolean))
      : view.props.style;
    expect(flatStyle.borderColor).toBe('#FEF2F2');
  });

  it('uses custom borderColor when provided', () => {
    const { UNSAFE_getByType } = render(
      <Badge {...defaultProps} borderColor="#FECACA" />,
    );
    const { View } = require('react-native');
    const view = UNSAFE_getByType(View);
    const flatStyle = Array.isArray(view.props.style)
      ? Object.assign({}, ...view.props.style.filter(Boolean))
      : view.props.style;
    expect(flatStyle.borderColor).toBe('#FECACA');
  });

  it('has borderWidth of 1', () => {
    const { UNSAFE_getByType } = render(<Badge {...defaultProps} />);
    const { View } = require('react-native');
    const view = UNSAFE_getByType(View);
    const flatStyle = Array.isArray(view.props.style)
      ? Object.assign({}, ...view.props.style.filter(Boolean))
      : view.props.style;
    expect(flatStyle.borderWidth).toBe(1);
  });
});
