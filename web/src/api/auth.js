import request from './index'

export function login(username, password) {
  return request.post('/auth/login', { username, password })
}

export function changePassword(oldPassword, newPassword) {
  return request.post('/auth/change-password', {
    old_password: oldPassword,
    new_password: newPassword
  })
}

export function getMe() {
  return request.get('/auth/me')
}
