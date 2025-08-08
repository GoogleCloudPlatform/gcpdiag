# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Custom datatype."""
import re


class Email:
  """Custom datatype for validating GCP email addresses.

  This class provides functionality to validate email addresses
  using a regular expression. It ensures that the email address
  conforms to the standard email format.

  Attributes:
      EMAIL_REGEX (Pattern): A compiled regular expression for email validation.
  """
  EMAIL_REGEX = re.compile(r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$')

  def __init__(self, email: str):
    """Initialize an Email object.

    Args:
        email (str): The email address to validate and store.
    """
    if not self.is_valid(email):
      raise ValueError(f'Invalid email address: {email}')
    self.email = email

  @staticmethod
  def is_valid(email: str) -> bool:
    """Check if the provided email address is valid.

    Args:
        email (str): The email address to validate.

    Returns:
        bool: True if the email address is valid, False otherwise.
    """
    return bool(Email.EMAIL_REGEX.match(email))

  def __str__(self):
    """Return the string representation of the email address."""
    return self.email

  def __eq__(self, other):
    """Check if two Email objects are equal."""
    return isinstance(other, Email) and self.email == other.email

  def __repr__(self):
    """Return the official string representation of the Email object."""
    return f'Email({self.email})'
