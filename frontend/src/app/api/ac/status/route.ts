// path: frontend/src/app/api/ac/status/route.ts
import { NextResponse } from 'next/server'
import axios from 'axios'
import { API_BASE_URL } from '../constants'

export async function GET() {
  try {
    const { data } = await axios.get(API_BASE_URL + '/status')
    return NextResponse.json(data)
  } catch (error) {
    console.error('Error fetching AC status:', error)
    return NextResponse.json(
      { error: error instanceof Error ? error.message : 'Unknown error occurred' },
      { status: 500 }
    )
  }
}