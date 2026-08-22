import React from 'react';
import { render, fireEvent } from '@testing-library/react-native';
import { Button } from '../src/Button';

describe('Button', () => {
  const defaultProps = {
    title: 'Press Me',
    onPress: jest.fn(),
  };

  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('rendering', () => {
    it('renders with title text', () => {
      const { getByText } = render(<Button {...defaultProps} />);
      expect(getByText('Press Me')).toBeTruthy();
    });

    it('renders with a custom title', () => {
      const { getByText } = render(<Button {...defaultProps} title="Submit" />);
      expect(getByText('Submit')).toBeTruthy();
    });
  });

  describe('onPress', () => {
    it('calls onPress when pressed', () => {
      const onPress = jest.fn();
      const { getByText } = render(<Button {...defaultProps} onPress={onPress} />);
      fireEvent.press(getByText('Press Me'));
      expect(onPress).toHaveBeenCalledTimes(1);
    });

    it('does not call onPress multiple times for single press', () => {
      const onPress = jest.fn();
      const { getByText } = render(<Button {...defaultProps} onPress={onPress} />);
      fireEvent.press(getByText('Press Me'));
      expect(onPress).toHaveBeenCalledTimes(1);
    });
  });

  describe('loading state', () => {
    it('shows activity indicator when loading is true', () => {
      const { queryByText, UNSAFE_getByType } = render(
        <Button {...defaultProps} loading={true} />,
      );
      // Title text should not be visible when loading
      expect(queryByText('Press Me')).toBeNull();
      // ActivityIndicator should be rendered
      const { ActivityIndicator } = require('react-native');
      expect(UNSAFE_getByType(ActivityIndicator)).toBeTruthy();
    });

    it('does not show activity indicator when loading is false', () => {
      const { getByText } = render(<Button {...defaultProps} loading={false} />);
      expect(getByText('Press Me')).toBeTruthy();
    });

    it('is disabled when loading', () => {
      const onPress = jest.fn();
      const { UNSAFE_getByType } = render(
        <Button {...defaultProps} onPress={onPress} loading={true} />,
      );
      const { TouchableOpacity } = require('react-native');
      const touchable = UNSAFE_getByType(TouchableOpacity);
      expect(touchable.props.disabled).toBe(true);
    });
  });

  describe('disabled state', () => {
    it('is disabled when disabled=true', () => {
      const onPress = jest.fn();
      const { UNSAFE_getByType } = render(
        <Button {...defaultProps} onPress={onPress} disabled={true} />,
      );
      const { TouchableOpacity } = require('react-native');
      const touchable = UNSAFE_getByType(TouchableOpacity);
      expect(touchable.props.disabled).toBe(true);
    });

    it('has reduced opacity when disabled', () => {
      const { UNSAFE_getByType } = render(
        <Button {...defaultProps} disabled={true} />,
      );
      const { TouchableOpacity } = require('react-native');
      const touchable = UNSAFE_getByType(TouchableOpacity);
      const flatStyle = Array.isArray(touchable.props.style)
        ? Object.assign({}, ...touchable.props.style)
        : touchable.props.style;
      expect(flatStyle.opacity).toBe(0.5);
    });

    it('has full opacity when not disabled', () => {
      const { UNSAFE_getByType } = render(
        <Button {...defaultProps} disabled={false} />,
      );
      const { TouchableOpacity } = require('react-native');
      const touchable = UNSAFE_getByType(TouchableOpacity);
      const flatStyle = Array.isArray(touchable.props.style)
        ? Object.assign({}, ...touchable.props.style)
        : touchable.props.style;
      expect(flatStyle.opacity).toBe(1);
    });
  });

  describe('variants', () => {
    it('renders primary variant (default)', () => {
      const { getByText } = render(<Button {...defaultProps} variant="primary" />);
      expect(getByText('Press Me')).toBeTruthy();
    });

    it('renders secondary variant', () => {
      const { getByText } = render(<Button {...defaultProps} variant="secondary" />);
      expect(getByText('Press Me')).toBeTruthy();
    });

    it('renders destructive variant', () => {
      const { getByText } = render(<Button {...defaultProps} variant="destructive" />);
      expect(getByText('Press Me')).toBeTruthy();
    });

    it('renders ghost variant', () => {
      const { getByText } = render(<Button {...defaultProps} variant="ghost" />);
      expect(getByText('Press Me')).toBeTruthy();
    });

    it('renders outline variant', () => {
      const { getByText } = render(<Button {...defaultProps} variant="outline" />);
      expect(getByText('Press Me')).toBeTruthy();
    });

    it('outline variant has a visible border', () => {
      const { UNSAFE_getByType } = render(
        <Button {...defaultProps} variant="outline" />,
      );
      const { TouchableOpacity } = require('react-native');
      const touchable = UNSAFE_getByType(TouchableOpacity);
      const flatStyle = Array.isArray(touchable.props.style)
        ? Object.assign({}, ...touchable.props.style)
        : touchable.props.style;
      expect(flatStyle.borderWidth).toBe(1);
    });

    it('ghost variant has transparent background', () => {
      const { UNSAFE_getByType } = render(
        <Button {...defaultProps} variant="ghost" />,
      );
      const { TouchableOpacity } = require('react-native');
      const touchable = UNSAFE_getByType(TouchableOpacity);
      const flatStyle = Array.isArray(touchable.props.style)
        ? Object.assign({}, ...touchable.props.style)
        : touchable.props.style;
      expect(flatStyle.backgroundColor).toBe('transparent');
    });
  });

  describe('sizes', () => {
    it('renders sm size', () => {
      const { getByText } = render(<Button {...defaultProps} size="sm" />);
      expect(getByText('Press Me')).toBeTruthy();
    });

    it('renders md size (default)', () => {
      const { getByText } = render(<Button {...defaultProps} size="md" />);
      expect(getByText('Press Me')).toBeTruthy();
    });

    it('renders lg size', () => {
      const { getByText } = render(<Button {...defaultProps} size="lg" />);
      expect(getByText('Press Me')).toBeTruthy();
    });
  });

  describe('icon', () => {
    it('renders icon when provided', () => {
      const { Text } = require('react-native');
      const icon = React.createElement(Text, { testID: 'icon' }, 'X');
      const { getByTestId, getByText } = render(
        <Button {...defaultProps} icon={icon} />,
      );
      expect(getByTestId('icon')).toBeTruthy();
      expect(getByText('Press Me')).toBeTruthy();
    });
  });
});
